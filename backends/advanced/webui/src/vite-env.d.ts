/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string
  readonly VITE_USER_LOOP_MODAL_ENABLED?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
