import { CloudwaysClient } from "./client.js";
import { firstNumber, firstString, JsonRecord } from "./utils.js";

export class DeployApi {
  constructor(private readonly client: CloudwaysClient) {}

  async deploy(serverId: string, appId: string, gitBranch = "main", commitMessage?: string) {
    const data = await this.client.request<JsonRecord>(
      "POST",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/deployment`,
      {
        git_branch: gitBranch,
        commit_message: commitMessage,
      },
    );

    return {
      deployment_id: firstString(data, ["deployment_id", "id"], "latest"),
      status: firstString(data, ["status"], "pending"),
      started_at: firstString(data, ["started_at", "created_at"], new Date().toISOString()),
      estimated_time: data.estimated_time ?? data.eta,
      raw: data,
    };
  }

  async checkDeploymentStatus(serverId: string, appId: string, deploymentId: string) {
    const data = await this.client.request<JsonRecord>(
      "GET",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/deployment-status`,
      undefined,
      { params: { deployment_id: deploymentId } },
    );

    return {
      status: firstString(data, ["status"], "pending"),
      progress: firstNumber(data, ["progress", "percentage"]),
      logs: data.logs ?? data.log_tail ?? [],
      completed_at: firstString(data, ["completed_at", "finished_at"]),
      raw: data,
    };
  }
}

