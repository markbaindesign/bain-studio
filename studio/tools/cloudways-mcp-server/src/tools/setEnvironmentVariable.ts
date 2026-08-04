import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { AppTargetSchema } from "../schemas/app.schema.js";
import { ToolContext } from "./context.js";

const SetInputSchema = AppTargetSchema.extend({
  variable_name: z.string().min(1),
  variable_value: z.string(),
});

export function registerEnvironmentVariableTools(server: McpServer, context: ToolContext) {
  server.registerTool(
    "set-environment-variable",
    {
      title: "Set Environment Variable",
      description: "Set or update an environment variable for a Cloudways application.",
      inputSchema: SetInputSchema,
    },
    async (input) => {
      try {
        return jsonContent(
          await context.applications.setEnvironmentVariable(
            input.server_id,
            input.app_id,
            input.variable_name,
            input.variable_value,
          ),
        );
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "list-environment-variables",
    {
      title: "List Environment Variables",
      description: "List Cloudways environment variable names without exposing sensitive values.",
      inputSchema: AppTargetSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.applications.listEnvironmentVariables(input.server_id, input.app_id));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

