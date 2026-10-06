#!/usr/bin/env python3
"""
Hands-free voice agent: talk to an OpenAI Realtime voice, which hands studio work
to background Claude sessions (studio/voice/tasks.py) and reads the results back.

Usage:
    python3 studio/voice/agent.py            # gpt-realtime-mini
    python3 studio/voice/agent.py --full     # gpt-realtime, better tool use, ~4x cost
    python3 studio/voice/agent.py --duplex   # headphones only: mic stays live while it talks

Ctrl+C ends the session. Running Claude tasks are terminated with it.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tasks import TaskRunner, Task  # noqa: E402

SAMPLE_RATE = 24000
CHANNELS = 1
DTYPE = "int16"
CHUNK_FRAMES = int(SAMPLE_RATE * 0.1)  # 100ms chunks
# How long after the last played chunk the mic stays gated, so the speakers'
# echo is not taken for Mark talking.
GATE_TAIL_S = 0.25
# Realtime sessions end after 60 minutes; reconnect a little before that.
SESSION_MAX_S = 55 * 60
# Longest task result passed to the voice model; the full text goes to the transcript.
RESULT_SPOKEN_CHARS = 1500

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system-prompt.md"
TRANSCRIPT_DIR = Path("/media/data/Dropbox/Work/Studio/context/voice-agent")
ENV_PATH = Path("/media/data/dev/bain-studio/studio/.env")

MINI_MODEL = "gpt-realtime-mini"
FULL_MODEL = "gpt-realtime"

TOOLS = [
    {
        "type": "function",
        "name": "start_task",
        "description": "Start a background Claude task with full studio access. Returns at once with a task id.",
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Complete, self-contained brief for Claude."},
                "project": {"type": "string", "description": "Studio project prefix, e.g. BD or NORE. Omit for studio-wide work."},
            },
            "required": ["instruction"],
        },
    },
    {
        "type": "function",
        "name": "list_tasks",
        "description": "List all tasks this session with their status.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_task_result",
        "description": "Get the full result of a task.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "type": "function",
        "name": "follow_up",
        "description": "Send a further message to a finished task's Claude session.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "message": {"type": "string"},
                "confirm_outward": {
                    "type": "boolean",
                    "description": "True only when Mark has just explicitly approved the action the task asked to confirm (sending, pushing, merging).",
                },
            },
            "required": ["task_id", "message"],
        },
    },
    {
        "type": "function",
        "name": "cancel_task",
        "description": "Stop a running task.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
]


def load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


class VoiceAgent:
    def __init__(self, model: str, api_key: str, duplex: bool):
        self.model = model
        self.api_key = api_key
        self.duplex = duplex
        self.runner = TaskRunner(on_finish=self.on_task_finished)
        self.transcript: list[tuple[str, str]] = []
        self.started = datetime.now()

        self.ws = None
        self.response_active = False
        self.user_speaking = False
        self.pending_notes: list[str] = []

        self.mic_gate_until = 0.0
        self.mic_queue: queue.Queue = queue.Queue()
        self.play_queue: queue.Queue = queue.Queue()

    # --- audio -------------------------------------------------------------

    def _mic_callback(self, indata, frames, time_info, status):
        self.mic_queue.put(bytes(indata))

    def _playback_thread(self):
        with sd.OutputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE) as stream:
            while True:
                chunk = self.play_queue.get()
                if chunk is None:
                    break
                stream.write(np.frombuffer(chunk, dtype=np.int16))
                self.mic_gate_until = time.monotonic() + GATE_TAIL_S

    async def _send_mic(self):
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
                            blocksize=CHUNK_FRAMES, callback=self._mic_callback):
            while True:
                await asyncio.sleep(0.01)
                while not self.mic_queue.empty():
                    chunk = self.mic_queue.get_nowait()
                    if not self.duplex and time.monotonic() < self.mic_gate_until:
                        continue
                    if self.ws is None:
                        continue
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode(),
                    }))

    # --- task notifications --------------------------------------------------

    async def on_task_finished(self, task: Task):
        self.transcript.append((f"Task {task.id} {task.status}", task.result))
        print(f"\n[task {task.id} {task.status}] {task.result[:300]}", flush=True)
        result = task.result[:RESULT_SPOKEN_CHARS]
        self.pending_notes.append(
            f"[Task update, not from Mark] Task {task.id} {task.status}. Result: {result}")

    async def _flush_notes(self):
        """Speak task updates only when nobody is talking, so they never collide
        with an active response or cut Mark off."""
        while True:
            await asyncio.sleep(0.5)
            if not self.pending_notes or self.ws is None:
                continue
            if self.response_active or self.user_speaking or not self.play_queue.empty():
                continue
            note = self.pending_notes.pop(0)
            await self._send_text(note)
            await self._create_response()

    async def _send_text(self, text: str):
        await self.ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "message", "role": "user",
                     "content": [{"type": "input_text", "text": text}]},
        }))

    async def _create_response(self):
        self.response_active = True
        await self.ws.send(json.dumps({"type": "response.create"}))

    # --- tools -------------------------------------------------------------

    async def _call_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "start_task":
                task = await self.runner.start(args["instruction"], args.get("project"))
                self.transcript.append((f"Task {task.id} started", args["instruction"]))
                print(f"\n[task {task.id} started] {args['instruction']}", flush=True)
                return {"task_id": task.id, "status": "started"}
            if name == "list_tasks":
                return {"tasks": self.runner.summary()}
            if name == "get_task_result":
                task = self.runner.result(int(args["task_id"]))
                return {"task_id": task.id, "status": task.status, "result": task.result[:RESULT_SPOKEN_CHARS]}
            if name == "follow_up":
                outward = bool(args.get("confirm_outward"))
                task = await self.runner.follow_up(int(args["task_id"]), args["message"], allow_outward=outward)
                self.transcript.append((f"Task {task.id} follow-up{' (outward allowed)' if outward else ''}",
                                        args["message"]))
                return {"task_id": task.id, "status": "running"}
            if name == "cancel_task":
                task = await self.runner.cancel(int(args["task_id"]))
                return {"task_id": task.id, "status": task.status}
            return {"error": f"Unknown tool {name}"}
        except Exception as exc:  # reported to the voice model so it can tell Mark
            return {"error": str(exc)}

    async def _handle_response_done(self, event: dict):
        calls = [item for item in event.get("response", {}).get("output", [])
                 if item.get("type") == "function_call"]
        if not calls:
            return
        for call in calls:
            try:
                args = json.loads(call.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            output = await self._call_tool(call["name"], args)
            await self.ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {"type": "function_call_output", "call_id": call["call_id"],
                         "output": json.dumps(output)},
            }))
        await self._create_response()

    # --- session -----------------------------------------------------------

    async def _receive(self):
        ai_buf = ""
        async for raw in self.ws:
            event = json.loads(raw)
            etype = event.get("type", "")

            if etype == "response.created":
                self.response_active = True
            elif etype == "response.done":
                self.response_active = False
                await self._handle_response_done(event)
            elif etype == "response.output_audio.delta":
                self.play_queue.put(base64.b64decode(event["delta"]))
            elif etype == "response.output_audio_transcript.delta":
                if not ai_buf:
                    print("\n[Agent] ", end="", flush=True)
                ai_buf += event.get("delta", "")
                print(event.get("delta", ""), end="", flush=True)
            elif etype == "response.output_audio_transcript.done":
                if ai_buf.strip():
                    self.transcript.append(("Agent", ai_buf.strip()))
                ai_buf = ""
                print()
            elif etype == "input_audio_buffer.speech_started":
                self.user_speaking = True
                with self.play_queue.mutex:
                    self.play_queue.queue.clear()
            elif etype == "input_audio_buffer.speech_stopped":
                self.user_speaking = False
            elif etype == "conversation.item.input_audio_transcription.completed":
                text = event.get("transcript", "").strip()
                if text:
                    print(f"\n[You] {text}", flush=True)
                    self.transcript.append(("You", text))
            elif etype == "error":
                print(f"\nError: {event.get('error', {}).get('message', event)}", file=sys.stderr)

    async def _session(self, first: bool):
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with websockets.connect(url, extra_headers=headers) as ws:
            await ws.recv()  # session.created
            self.ws = ws
            self.response_active = False
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "instructions": SYSTEM_PROMPT_PATH.read_text(),
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "audio": {
                        "input": {
                            "transcription": {"model": "gpt-4o-mini-transcribe"},
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "prefix_padding_ms": 300,
                                "silence_duration_ms": 700,
                            },
                        },
                        "output": {"voice": "alloy"},
                    },
                },
            }))
            if first:
                await self._send_text("[Session start, not from Mark] Greet Mark in a few words and ask what he needs.")
            else:
                # A fresh session has no memory of the last one; hand it the task list.
                await self._send_text("[Reconnected, not from Mark] Current tasks: "
                                      + json.dumps(self.runner.summary())
                                      + " Say nothing unless Mark speaks.")
            if first:
                await self._create_response()
            recv = asyncio.create_task(self._receive())
            try:
                await asyncio.wait_for(asyncio.shield(recv), timeout=SESSION_MAX_S)
            except asyncio.TimeoutError:
                recv.cancel()
            finally:
                self.ws = None

    async def run(self):
        threading.Thread(target=self._playback_thread, daemon=True).start()
        mic = asyncio.create_task(self._send_mic())
        notes = asyncio.create_task(self._flush_notes())
        first = True
        fast_failures = 0
        try:
            while True:
                print(f"\nConnecting to {self.model}...", flush=True)
                began = time.monotonic()
                try:
                    await self._session(first)
                except (websockets.ConnectionClosed, OSError) as exc:
                    print(f"\nConnection closed ({exc}).", file=sys.stderr)
                first = False
                # A session that dies within a minute is a rejected key, quota or
                # config, not the 60-minute limit; stop rather than loop on it.
                fast_failures = fast_failures + 1 if time.monotonic() - began < 60 else 0
                if fast_failures >= 3:
                    print("\nThree quick disconnects in a row; giving up.", file=sys.stderr)
                    return
                await asyncio.sleep(2 * fast_failures + 1)
        finally:
            mic.cancel()
            notes.cancel()
            for task in self.runner.running():
                await self.runner.cancel(task.id)
            self.play_queue.put(None)

    def save_transcript(self):
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        path = TRANSCRIPT_DIR / f"{self.started.strftime('%Y-%m-%d-%H%M')}.md"
        mins, secs = divmod(int((datetime.now() - self.started).total_seconds()), 60)
        lines = [f"# Voice agent session {self.started.strftime('%Y-%m-%d %H:%M')}",
                 f"Model: {self.model}  Duration: {mins:02d}:{secs:02d}", "", "---", ""]
        for speaker, text in self.transcript:
            lines += [f"**{speaker}:** {text}", ""]
        path.write_text("\n".join(lines))
        print(f"\nTranscript saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Hands-free studio voice agent")
    parser.add_argument("--full", action="store_true", help="Use gpt-realtime (~4x cost, better tool use)")
    parser.add_argument("--duplex", action="store_true",
                        help="Keep the mic live while the agent speaks. Headphones only.")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("Error: OPENAI_API_KEY not set. Add it to studio/.env or export it.", file=sys.stderr)
        sys.exit(1)

    agent = VoiceAgent(FULL_MODEL if args.full else MINI_MODEL, api_key, args.duplex)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nSession ended.")
    finally:
        agent.save_transcript()


if __name__ == "__main__":
    main()
