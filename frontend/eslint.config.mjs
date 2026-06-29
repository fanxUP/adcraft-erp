// @ts-check
import pluginVue from 'eslint-plugin-vue'
import { withVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'

export default withVueTs(
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  {
    name: 'app/no-explicit-any',
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    name: 'app/ignores',
    ignores: ['dist/', 'node_modules/'],
  },
)
