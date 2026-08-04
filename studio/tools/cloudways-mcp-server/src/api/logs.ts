import { CloudwaysClient } from "./client.js";
import { JsonRecord, toArray } from "./utils.js";

export type LogType = "application" | "error" | "access" | "deployment";

export class LogsApi {
  constructor(private readonly client: CloudwaysClient) {}

  async getLogs(serverId: string, appId: string, logType: LogType, lines = 50): Promise<string[]> {
    const data = await this.client.request<unknown>(
      "GET",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/logs`,
      undefined,
      { params: { log_type: logType, lines } },
    );

    if (typeof data === "string") return data.split(/\r?\n/).filter(Boolean);
    const array = toArray<JsonRecord | string>(data);
    return array.map((line) => (typeof line === "string" ? line : JSON.stringify(line)));
  }
}

