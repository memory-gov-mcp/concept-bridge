import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "public/mockServiceWorker.js"] },
  tseslint.configs.recommended,
);
