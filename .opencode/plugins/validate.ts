import type { Plugin } from "@opencode-ai/plugin";

const ARTICLES_GLOB = /knowledge\/articles\/.*\.json/;

const validatePlugin: Plugin = async (input) => {
  const { $ } = input;

  return {
    async "tool.execute.after"(event) {
      const toolName = event.tool;
      if (toolName !== "write" && toolName !== "edit") return;

      const filePath: unknown = event.args?.file_path ?? event.args?.filePath;
      if (typeof filePath !== "string") return;
      if (!ARTICLES_GLOB.test(filePath)) return;

      try {
        const result = await $`python3 hooks/validate_json.py ${filePath}`.nothrow();
        console.log(`[validate] ${filePath} (exit: ${result.exitCode})`);
        if (result.exitCode !== 0) {
          console.warn(`[validate] FAILED:\n${result.stdout.toString()}`);
          if (result.stderr.length) {
            console.error(`[validate] stderr:\n${result.stderr.toString()}`);
          }
        }
      } catch (err) {
        console.error(`[validate] Unexpected error running validator: ${String(err)}`);
      }
    },
  };
};

export default validatePlugin;
