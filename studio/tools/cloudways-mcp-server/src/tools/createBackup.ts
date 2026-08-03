import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { AppTargetSchema } from "../schemas/app.schema.js";
import { ToolContext } from "./context.js";

const CreateInputSchema = AppTargetSchema.extend({
  backup_name: z.string().optional(),
});

export function registerBackupTools(server: McpServer, context: ToolContext) {
  server.registerTool(
    "create-cloudways-backup",
    {
      title: "Create Cloudways Backup",
      description: "Create an on-demand backup for a Cloudways application.",
      inputSchema: CreateInputSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.backups.createBackup(input.server_id, input.app_id, input.backup_name));
      } catch (error) {
        return toolError(error);
      }
    },
  );

  server.registerTool(
    "list-cloudways-backups",
    {
      title: "List Cloudways Backups",
      description: "List backups and their metadata for a Cloudways application.",
      inputSchema: AppTargetSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.backups.listBackups(input.server_id, input.app_id));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

