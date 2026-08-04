import { CloudwaysClient } from "./client.js";
import { firstString, JsonRecord, toArray } from "./utils.js";

export type SslAction = "list" | "enable_auto" | "install_custom";

export class SslApi {
  constructor(private readonly client: CloudwaysClient) {}

  async manageCertificate(
    serverId: string,
    appId: string,
    action: SslAction,
    certificateContent?: string,
    keyContent?: string,
  ) {
    if (action === "list") {
      const data = await this.client.request<JsonRecord>(
        "GET",
        `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/ssl`,
      );
      return this.normalizeSsl(data);
    }

    const data = await this.client.request<JsonRecord>(
      "POST",
      `/servers/${encodeURIComponent(serverId)}/apps/${encodeURIComponent(appId)}/ssl-certificate`,
      {
        action,
        certificate_content: certificateContent,
        key_content: keyContent,
      },
    );
    return this.normalizeSsl(data);
  }

  private normalizeSsl(data: JsonRecord) {
    return {
      status: firstString(data, ["status"], "unknown"),
      expiry_date: firstString(data, ["expiry_date", "expires_at"]),
      installed_certificates: toArray<JsonRecord>(data.installed_certificates ?? data.certificates ?? data),
      raw: data,
    };
  }
}

