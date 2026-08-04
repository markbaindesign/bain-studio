import { ServersApi } from "./servers.js";

export class MonitoringApi {
  constructor(private readonly serversApi: ServersApi) {}

  getServerStats(serverId: string) {
    return this.serversApi.getServerStats(serverId);
  }
}

