import { build } from "esbuild";
import { mkdir, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const workspaceDirectory = fileURLToPath(new URL("..", import.meta.url));
const outputDirectory = fileURLToPath(new URL("../static/dist", import.meta.url));

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });

await build({
  entryPoints: [fileURLToPath(new URL("../frontend/src/main.jsx", import.meta.url))],
  absWorkingDir: workspaceDirectory,
  bundle: true,
  minify: true,
  sourcemap: false,
  outfile: fileURLToPath(new URL("../static/dist/app.js", import.meta.url)),
  define: { "process.env.NODE_ENV": '"production"' },
  loader: { ".jsx": "jsx" },
});
