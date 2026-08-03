import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createToolContext } from "./context.js";
import { registerBackupTools } from "./createBackup.js";
import { registerDeployProjectTools } from "./deployProject.js";
import { registerGetServerStatsTool } from "./getServerStats.js";
import { registerListApplicationsTool } from "./listApplications.js";
import { registerListServersTool } from "./listServers.js";
import { registerManageSslTool } from "./manageSSL.js";
import { registerRestartServiceTool } from "./restartService.js";
import { registerEnvironmentVariableTools } from "./setEnvironmentVariable.js";
import { registerViewLogsTool } from "./viewLogs.js";

export function registerCloudwaysTools(server: McpServer) {
  const context = createToolContext();

  registerListServersTool(server, context);
  registerListApplicationsTool(server, context);
  registerGetServerStatsTool(server, context);
  registerDeployProjectTools(server, context);
  registerViewLogsTool(server, context);
  registerEnvironmentVariableTools(server, context);
  registerManageSslTool(server, context);
  registerBackupTools(server, context);
  registerRestartServiceTool(server, context);
}

