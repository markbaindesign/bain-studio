import { CloudwaysClient } from "./client.js";
import { firstNumber, firstString, JsonRecord, toArray } from "./utils.js";

export class BackupsApi {
  constructor(private readonly client: CloudwaysClient) {}

  async createBackup(serverId: string, appId: string, backupName?: string) {
    const data = await this.client.request<JsonRecord>(
      "POST",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/backup`,
      backupName ? { backup_name: backupName } : {},
    );

    return {
      backup_id: firstString(data, ["backup_id", "id"], "latest"),
      status: firstString(data, ["status"], "pending"),
      size_mb: firstNumber(data, ["size_mb", "size"]),
      created_at: firstString(data, ["created_at"], new Date().toISOString()),
      raw: data,
    };
  }

  async listBackups(serverId: string, appId: string) {
    const data = await this.client.request(
      "GET",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/backups`,
    );
    return toArray<JsonRecord>(data);
  }
}

