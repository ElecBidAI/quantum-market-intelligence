import { loadEnv } from "@qmi/config";
import { buildApp } from "./app.js";

const env = loadEnv();
const app = buildApp();

app
  .listen({ port: env.API_PORT, host: "0.0.0.0" })
  .then((address) => {
    app.log.info(`qmi-api listening on ${address}`);
  })
  .catch((error: unknown) => {
    app.log.error(error);
    process.exit(1);
  });
