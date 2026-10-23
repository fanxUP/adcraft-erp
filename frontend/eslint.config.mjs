// @ts-check
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default tseslint.config(
  pluginVue.configs['flat/essential'],
  ...tseslint.configs.recommended,
  {
    name: 'app/vue-typescript-parser',
    files: ['*.vue', '**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: {
          js: 'espree',
          jsx: 'espree',
          ts: tseslint.parser,
          tsx: tseslint.parser,
        },
        ecmaVersion: 2024,
        extraFileExtensions: ['.vue'],
      },
    },
    rules: {
      'vue/block-lang': ['error', { script: { lang: ['ts'], allowNoLang: true } }],
    },
  },
  {
    name: 'app/no-explicit-any',
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
    },
  },
  {
    name: 'app/ignores',
    ignores: [
      'node_modules/**',
      'dist/**',
      'dist.bak-*/**',
      '**/dist.bak-*/**',
      '**/*.bak-*',
      '**/*.bak-*/**',
    ],
  },
)
