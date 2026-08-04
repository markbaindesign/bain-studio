# Cloudways MCP Server

Servidor MCP para operar Cloudways desde Claude Code u otros clientes MCP.

> Nota importante: la documentacion publica de Cloudways indica que API V1 llega a fin de vida el 31 de marzo de 2026. Este paquete sigue la estructura V1 del brief original, con `CLOUDWAYS_API_BASE_URL` configurable para poder migrar endpoints a V2 sin reescribir los tools.

## Tools incluidos

- `list-cloudways-servers`
- `list-cloudways-apps`
- `get-server-stats`
- `deploy-cloudways-app`
- `check-deployment-status`
- `get-cloudways-logs`
- `set-environment-variable`
- `list-environment-variables`
- `manage-ssl-certificate`
- `create-cloudways-backup`
- `list-cloudways-backups`
- `restart-cloudways-service`

## Instalacion local

```bash
npm install
npm run build
```

Configura credenciales:

```bash
cp .env.example .env
```

```env
CLOUDWAYS_EMAIL=tu_email@example.com
CLOUDWAYS_API_TOKEN=tu_api_token
CLOUDWAYS_LOG_LEVEL=info
CLOUDWAYS_API_BASE_URL=https://api.cloudways.com/api/v1
```

## Uso con Claude Code

Ejemplo de configuracion MCP:

```json
{
  "mcpServers": {
    "cloudways": {
      "command": "node",
      "args": ["C:/Claude/empaya/cloudways-mcp-server/dist/index.js"],
      "env": {
        "CLOUDWAYS_EMAIL": "tu_email@example.com",
        "CLOUDWAYS_API_TOKEN": "tu_api_token"
      }
    }
  }
}
```

Tambien puedes ejecutar:

```bash
npm run dev
```

## Seguridad

- No commitees `.env` ni tokens.
- `list-environment-variables` redacta valores sensibles.
- Los certificados SSL custom se pasan solo en la llamada MCP y no se escriben en disco.

## Desarrollo

```bash
npm run typecheck
npm run build
```

Los endpoints estan centralizados en `src/api/*`. Si Cloudways V2 usa rutas distintas, ajusta esas clases y los nombres de tools pueden quedarse estables.
