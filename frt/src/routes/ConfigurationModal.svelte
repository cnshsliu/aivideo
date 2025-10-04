<script lang="ts">
  export let showConfigModal: boolean;
  export let videoConfig: {
    sort: string;
    keepClipLength: boolean;
    length: number | null;
    clipNum: number | null;
    title: string;
    keepTitle: boolean;
    open: boolean;
    titleTimestamp: boolean;
    titleLength: number | null;
    titleFont: string;
    titleFontSize: number;
    titlePosition: number;
    subtitleFont: string;
    subtitleFontSize: number;
    subtitlePosition: number;
    clipSilent: boolean;
    genSubtitle: boolean;
    genVoice: boolean;
    llmProvider: string;
    text: string;
    mp3: string;
    bgmFadeIn: number;
    bgmFadeOut: number;
    bgmVolume: number;
  };
  export let onClose: () => void;
</script>

{#if showConfigModal}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm overflow-y-auto"
  >
    <div
      class="w-full max-w-2xl max-h-[90vh] rounded-2xl bg-white p-6 shadow-xl overflow-y-auto"
    >
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold">Video Generation Configuration</h2>
        <button
          onclick={onClose}
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg
            class="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>
      </div>

      <div class="space-y-6">
        <!-- Media Settings -->
        <div class="border-b border-gray-200 pb-4">
          <h3 class="text-lg font-medium mb-4">Media Settings</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Sort Order</label
              >
              <select
                bind:value={videoConfig.sort}
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="alphnum">Alphanumeric</option>
                <option value="random">Random</option>
              </select>
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.keepClipLength}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Keep Clip Length</label
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Video Length (seconds)</label
              >
              <input
                type="number"
                bind:value={videoConfig.length}
                placeholder="Auto"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Number of Clips</label
              >
              <input
                type="number"
                bind:value={videoConfig.clipNum}
                placeholder="Auto"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- Title Settings -->
        <div class="border-b border-gray-200 pb-4">
          <h3 class="text-lg font-medium mb-4">Title Settings</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Title Text</label
              >
              <input
                type="text"
                bind:value={videoConfig.title}
                placeholder="Video title..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.keepTitle}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Keep Title Throughout Video</label
              >
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.open}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Open Video After Generation</label
              >
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.titleTimestamp}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Add Timestamp to Title</label
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Title Display Length (seconds)</label
              >
              <input
                type="number"
                bind:value={videoConfig.titleLength}
                step="0.1"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Title Font</label
              >
              <input
                type="text"
                bind:value={videoConfig.titleFont}
                placeholder="Arial"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Title Font Size</label
              >
              <input
                type="number"
                bind:value={videoConfig.titleFontSize}
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Title Position (% of screen height)</label
              >
              <input
                type="number"
                bind:value={videoConfig.titlePosition}
                min="0"
                max="100"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- Subtitle Settings -->
        <div class="border-b border-gray-200 pb-4">
          <h3 class="text-lg font-medium mb-4">Subtitle Settings</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Subtitle Font</label
              >
              <input
                type="text"
                bind:value={videoConfig.subtitleFont}
                placeholder="Arial"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Subtitle Font Size</label
              >
              <input
                type="number"
                bind:value={videoConfig.subtitleFontSize}
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Subtitle Position (% of screen height)</label
              >
              <input
                type="number"
                bind:value={videoConfig.subtitlePosition}
                min="0"
                max="100"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.genSubtitle}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Generate Subtitles</label
              >
            </div>
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.genVoice}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Generate Voice</label
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >LLM Provider</label
              >
              <select
                bind:value={videoConfig.llmProvider}
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              >
                <option value="qwen">Qwen</option>
                <option value="grok">Grok</option>
                <option value="glm">GLM</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Static Subtitle File</label
              >
              <input
                type="text"
                bind:value={videoConfig.text}
                placeholder="Path to subtitle file..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- Audio Settings -->
        <div class="border-b border-gray-200 pb-4">
          <h3 class="text-lg font-medium mb-4">Audio Settings</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex items-center">
              <input
                type="checkbox"
                bind:checked={videoConfig.clipSilent}
                class="mr-2"
              />
              <label class="text-sm font-medium text-gray-700"
                >Make Clips Silent</label
              >
            </div>
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Background Music File</label
              >
              <input
                type="text"
                bind:value={videoConfig.mp3}
                placeholder="Path to MP3 file..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >BGM Fade In (seconds)</label
              >
              <input
                type="number"
                bind:value={videoConfig.bgmFadeIn}
                step="0.1"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >BGM Fade Out (seconds)</label
              >
              <input
                type="number"
                bind:value={videoConfig.bgmFadeOut}
                step="0.1"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >BGM Volume (0.0-1.0)</label
              >
              <input
                type="number"
                bind:value={videoConfig.bgmVolume}
                step="0.1"
                min="0"
                max="1"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Actions -->
      <div class="mt-6 flex gap-3 justify-end">
        <button
          onclick={onClose}
          class="rounded-lg bg-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-400"
        >
          Cancel
        </button>
        <button
          class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600"
        >
          Save Configuration
        </button>
      </div>
    </div>
  </div>
{/if}
