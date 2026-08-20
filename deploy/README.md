# Deploy — olheiro.lumenscode.com.br

VPS: `213.199.53.216` (webbotss / Lumens)  
Nginx edge: container `back-nginx-1` (`/var/lib/jenkins/workspace/back/nginx.conf`)

## Portas

| Serviço | Host | Container |
|---|---|---|
| Web (Next.js) | `127.0.0.1:4090` | `3000` |
| API (Go) | `127.0.0.1:4091` | `8080` |

## URL pública

- Site: https://olheiro.lumenscode.com.br  
- Health API: https://olheiro.lumenscode.com.br/health  
- Webhook AbacatePay:  
  `https://olheiro.lumenscode.com.br/v1/billing/webhooks/abacatepay?webhookSecret=SEU_SECRET`

## 1) DNS

Registro **A**:

```
olheiro.lumenscode.com.br  →  213.199.53.216
```

## 2) TLS (certbot)

No host:

```bash
certbot certonly --nginx \
  -d lumenscode.com.br \
  -d hub.lumenscode.com.br \
  -d olheiro.lumenscode.com.br \
  --cert-name lumenscode.com.br \
  --expand
```

## 3) Nginx

Copiar o bloco de `deploy/nginx/olheiro.lumenscode.com.br.conf` para dentro do `http { }` em:

`/var/lib/jenkins/workspace/back/nginx.conf`

```bash
cd /var/lib/jenkins/workspace/back
# editar nginx.conf (colar upstreams + servers)
docker exec back-nginx-1 nginx -t
docker exec back-nginx-1 nginx -s reload
```

`extra_hosts: host.docker.internal:host-gateway` já existe no compose do `back`.

## 4) Jenkins

1. New Item → Pipeline → **Pipeline script from SCM**
2. Repo: `https://github.com/Davitfrota/Olheiro.git`
3. Script Path: `Jenkinsfile`
4. Credentials:
   - Git: `key-github` (ou o ID que você usa)
   - Secret file `.env`: `olheiro-env` (SUPABASE_* + ABACATEPAY_*)
5. Branch default: `main` (ou a branch com estes arquivos)

## 5) .env de produção (credential)

```
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
ABACATEPAY_API_KEY=
ABACATEPAY_WEBHOOK_SECRET=
ABACATEPAY_PRODUCT_ID=
ABACATEPAY_API_BASE=https://api.abacatepay.com/v2
```

## 6) Smoke local na VPS

```bash
curl -sI http://127.0.0.1:4090/ | head
curl -s http://127.0.0.1:4091/health
curl -sI -H 'Host: olheiro.lumenscode.com.br' https://127.0.0.1/ -k | head
```
