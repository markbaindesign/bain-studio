import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { ToolContext } from "./context.js";

const InputSchema = z.object({
  server_id: z.string().min(1),
  app_id: z.string().min(1),
  log_type: z.enum(["application", "error", "access", "deployment"]),
  lines: z.number().int().positive().max(1000).default(50),
});

export function registerViewLogsTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "get-cloudways-logs",
    {
      title: "Get Cloudways Logs",
      description: "Read recent Cloudways application, error, access, or deployment logs.",
      inputSchema: InputSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.logs.getLogs(input.server_id, input.app_id, input.log_type, input.lines));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

