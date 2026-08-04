import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { jsonContent, toolError } from "../api/utils.js";
import { DeploymentStatusSchema, DeploySchema } from "../schemas/deploy.schema.js";
import { ToolContext } from "./context.js";

export function registerDeployProjectTools(server: McpServer, context: ToolContext) {
  server.registerTool(
    "deploy-cloudways-app",
    {
      title: "Deploy Cloudways App",
      description: "Start a Git deployment for a Cloudways application.",
      inputSchema: DeploySchema,
    },
    async (input) => {
      try {
        return jsonContent(
          await context.deploy.deploy(input.server_id, input.app_id, input.git_branch, input.commit_message),
        );
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "check-deployment-status",
    {
      title: "Check Deployment Status",
      description: "Check progress and logs for a Cloudways deployment.",
      inputSchema: DeploymentStatusSchema,
    },
    async (input) => {
      try {
        return jsonContent(
          await context.deploy.checkDeploymentStatus(input.server_id, input.app_id, input.deployment_id),
        );
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

