# HTTPS / TLS

生产环境建议启用 HTTPS，尤其是在使用 SAML SSO 时。

## 证书准备

你需要两份 PEM 文件：

- `server.crt`：服务器证书（如有中间证书建议合并为 bundle）
- `server.key`：对应私钥

## 一键启用 HTTPS

```bash
cd deploy
./scripts/enable-tls.sh --cert /path/to/server.crt --key /path/to/server.key
```

脚本会自动：

1. 校验证书与私钥格式
2. 校验证书与私钥是否匹配
3. 复制到 `deploy/certs/`
4. 切换 Nginx 到 HTTPS 模式
5. 执行重启和冒烟验证

## 恢复为 HTTP

```bash
./scripts/disable-tls.sh
```

## 端口与证书更新

- 默认 HTTPS 端口是 443，可在 `deploy/.env` 中修改
- 证书更新时，重新运行 `enable-tls.sh` 即可完成覆盖

## 与 SSO 的关系

如果之前手工配置了 SAML 的 SP Entity ID 或 ACS URL，启用 HTTPS 后请同步改为 `https://`。
