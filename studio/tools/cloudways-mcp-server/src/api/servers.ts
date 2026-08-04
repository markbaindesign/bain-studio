import { CloudwaysClient } from "./client.js";
import { firstNumber, firstString, JsonRecord, toArray } from "./utils.js";

export type ServerFilter = "running" | "stopped" | "all";

export class ServersApi {
  constructor(private readonly client: CloudwaysClient) {}

  async listServers(filter: ServerFilter = "all") {
    const data = await this.client.request("GET", "/servers");
    const servers = toArray<JsonRecord>(data).map((server) => ({
      server_id: firstString(server, ["server_id", "id"]),
      label: firstString(server, ["label", "name", "server_name"]),
      status: firstString(server, ["status", "server_status"], "unknown"),
      ip_address: firstString(server, ["ip_address", "public_ip", "ip"]),
      created_at: firstString(server, ["created_at", "created_on"]),
    }));

    if (filter === "all") return servers;
    return servers.filter((server) => server.status.toLowerCase() === filter);
  }

  async getServerStats(serverId: string) {
    const data = await this.client.request<JsonRecord>("GET", `/servers/${encodeURIComponent(serverId)}/stats`);
    return {
      cpu_usage: firstNumber(data, ["cpu_usage", "cpu", "cpu_percent"]),
      ram_usage: firstNumber(data, ["ram_usage", "memory_usage", "ram_percent"]),
      disk_usage: firstNumber(data, ["disk_usage", "disk_percent"]),
      uptime: firstString(data, ["uptime", "server_uptime"]),
      load_average: data.load_average ?? data.load ?? data.loadavg,
      raw: data,
    };
  }

  async restartService(serverId: string, service: string) {
    const data = await this.client.request<JsonRecord>(
      "POST",
      `/servers/${encodeURIComponent(serverId)}/services/${encodeURIComponent(service)}/restart`,
    );

    return {
      service,
      previous_status: data.previous_status ?? data.before_status,
      new_status: data.new_status ?? data.status ?? "restart_requested",
      restarted_at: firstString(data, ["restarted_at", "updated_at"], new Date().toISOString()),
      raw: data,
    };
  }
}

