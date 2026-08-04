import { CloudwaysClient } from "./client.js";
import { firstString, JsonRecord, sanitizeEnvironmentVariables, toArray } from "./utils.js";

export class ApplicationsApi {
  constructor(private readonly client: CloudwaysClient) {}

  async listApplications(serverId: string) {
    const data = await this.client.request("GET", `/servers/${encodeURIComponent(serverId)}/apps`);
    return toArray<JsonRecord>(data).map((app) => ({
      app_id: firstString(app, ["app_id", "id", "application_id"]),
      app_name: firstString(app, ["app_name", "name", "label"]),
      app_status: firstString(app, ["app_status", "status"], "unknown"),
      domain: firstString(app, ["domain", "app_fqdn", "url"]),
      git_branch: firstString(app, ["git_branch", "branch"]),
      last_deployed: firstString(app, ["last_deployed", "last_deployment", "updated_at"]),
    }));
  }

  async setEnvironmentVariable(serverId: string, appId: string, variableName: string, variableValue: string) {
    const data = await this.client.request<JsonRecord>(
      "POST",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/environment-variable`,
      {
        variable_name: variableName,
        variable_value: variableValue,
      },
    );

    return {
      success: Boolean(data.success ?? true),
      message: firstString(data, ["message"], `Variable ${variableName} updated`),
    };
  }

  async listEnvironmentVariables(serverId: string, appId: string) {
    const data = await this.client.request(
      "GET",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/environment-variables`,
    );
    return sanitizeEnvironmentVariables(data);
  }
}

