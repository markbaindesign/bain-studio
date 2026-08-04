import { ApplicationsApi } from "../api/applications.js";
import { BackupsApi } from "../api/backups.js";
import { CloudwaysClient } from "../api/client.js";
import { DeployApi } from "../api/deploy.js";
import { LogsApi } from "../api/logs.js";
import { MonitoringApi } from "../api/monitoring.js";
import { ServersApi } from "../api/servers.js";
import { SslApi } from "../api/ssl.js";

export type ToolContext = {
  servers: ServersApi;
  applications: ApplicationsApi;
  deploy: DeployApi;
  logs: LogsApi;
  monitoring: MonitoringApi;
  backups: BackupsApi;
  ssl: SslApi;
};

export function createToolContext(): ToolContext {
  const client = new CloudwaysClient();
  const servers = new ServersApi(client);

  return {
    servers,
    applications: new ApplicationsApi(client),
    deploy: new DeployApi(client),
    logs: new LogsApi(client),
    monitoring: new MonitoringApi(servers),
    backups: new BackupsApi(client),
    ssl: new SslApi(client),
  };
}

