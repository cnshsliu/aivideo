<script lang="ts">
  import { onMount } from "svelte";

  interface Project {
    id: string;
    name: string;
    title: string;
    video_title: string;
    createdAt: string;
    updatedAt: string;
    prompt?: string;
    staticSubtitle?: string;
    keepTitle?: boolean;
    addTimestampToTitle?: boolean;
    titleFont?: string;
    titleFontSize?: number;
    titlePosition?: number;
    sortOrder?: string;
    keepClipLength?: boolean;
    clipNum?: number | null;
    subtitleFont?: string;
    subtitleFontSize?: number;
    subtitlePosition?: number;
    genSubtitle?: boolean;
    genVoice?: boolean;
    llmProvider?: string;
    bgmFile?: string;
    bgmFadeIn?: number;
    bgmFadeOut?: number;
    bgmVolume?: number;
  }

  interface Material {
    id: string;
    projectId: string;
    relativePath: string;
    fileName: string;
    fileType: string;
    alias: string;
    createdAt: string;
  }

  interface Props {
    selectedProject: Project;
    generatingVideo: boolean;
    showLogs: boolean;
    generationLogs: string;
    onGenerateVideo: () => void;
    onShowMaterialsModal: (onCloseCallback?: () => void) => void;
    onUpdateProject: (project: Project) => void;
    onPreviewMedia: (media: {
      type: "image" | "video";
      url: string;
      name: string;
      poster?: string;
    }) => void;
  }

  let {
    selectedProject,
    generatingVideo,
    showLogs,
    generationLogs,
    onGenerateVideo,
    onShowMaterialsModal,
    onUpdateProject,
    onPreviewMedia,
  }: Props = $props();

  let editingAliasId = $state<string | null>(null);
  let editingAliasValue = $state("");
  let loadingMaterials = $state(false);
  let projectMaterials = $state<Material[]>([]);

  // Computed property to sort project materials
  let sortedProjectMaterials = $derived(
    [...projectMaterials].sort((a, b) => {
      const aliasA = (a.alias || "").trim().toLowerCase();
      const aliasB = (b.alias || "").trim().toLowerCase();

      // Materials with alias starting with 'start' come first
      const isStartA = aliasA.startsWith("start");
      const isStartB = aliasB.startsWith("start");

      if (isStartA && !isStartB) return -1;
      if (!isStartA && isStartB) return 1;

      // Materials with alias starting with 'close' or 'closing' come last
      const isCloseA =
        aliasA.startsWith("close") || aliasA.startsWith("closing");
      const isCloseB =
        aliasB.startsWith("close") || aliasB.startsWith("closing");

      if (isCloseA && !isCloseB) return 1;
      if (!isCloseA && isCloseB) return -1;

      // If both are 'start' or both are 'close', sort alphabetically
      if (isStartA && isStartB) return aliasA.localeCompare(aliasB);
      if (isCloseA && isCloseB) return aliasA.localeCompare(aliasB);

      // Other materials sorted alphabetically by alias
      return aliasA.localeCompare(aliasB);
    }),
  );

  // Log sorted materials' aliases for debugging
  $effect(() => {
    console.log(
      "Sorted materials aliases:",
      sortedProjectMaterials.map((m) => m.alias),
    );
  });

  async function loadProjectMaterials() {
    if (!selectedProject) return;

    loadingMaterials = true;
    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
      );
      if (response.ok) {
        projectMaterials = await response.json();
      } else {
        console.error("Failed to load project materials");
        projectMaterials = [];
      }
    } catch (err) {
      console.error("Error loading project materials:", err);
      projectMaterials = [];
    } finally {
      loadingMaterials = false;
    }
  }

  function getMediaIcon(type: string): string {
    switch (type) {
      case "image":
        return "🖼️";
      case "video":
        return "🎥";
      case "audio":
        return "🎵";
      default:
        return "📄";
    }
  }

  $effect(() => {
    if (selectedProject) {
      loadProjectMaterials();
      staticSubtitleContent = selectedProject.staticSubtitle || "";
      promptContent = selectedProject.prompt || "hello";
      // Initialize title settings from selectedProject
      keepTitle = selectedProject.keepTitle ?? true;
      addTimestampToTitle = selectedProject.addTimestampToTitle ?? false;
      videoTitle = selectedProject.video_title ?? selectedProject.title;
      titleFont = selectedProject.titleFont ?? "Hiragino Sans GB";
      titleFontSize = selectedProject.titleFontSize ?? 24;
      titlePosition = selectedProject.titlePosition ?? 50;
      // Initialize media settings from selectedProject
      sortOrder = selectedProject.sortOrder ?? "alphnum";
      keepClipLength = selectedProject.keepClipLength ?? false;
      clipNum = selectedProject.clipNum ?? null;
      // Initialize subtitle settings from selectedProject
      subtitleFont = selectedProject.subtitleFont ?? "Hiragino Sans GB";
      subtitleFontSize = selectedProject.subtitleFontSize ?? 24;
      subtitlePosition = selectedProject.subtitlePosition ?? 50;
      genSubtitle = selectedProject.genSubtitle ?? true;
      genVoice = selectedProject.genVoice ?? false;
      llmProvider = selectedProject.llmProvider ?? "qwen";
      // Initialize audio settings from selectedProject
      bgmFile = selectedProject.bgmFile ?? "";
      bgmFadeIn = selectedProject.bgmFadeIn ?? 0.5;
      bgmFadeOut = selectedProject.bgmFadeOut ?? 0.5;
      bgmVolume = selectedProject.bgmVolume ?? 0.5;
    }
  });

  let isEditingTitle = $state(false);
  let editedTitle = $state("");
  let staticSubtitleContent = $state(selectedProject.staticSubtitle || "");
  let promptContent = $state(selectedProject.prompt || "hello");
  // Title settings state variables
  let keepTitle = $state(selectedProject.keepTitle ?? true);
  let addTimestampToTitle = $state(
    selectedProject.addTimestampToTitle ?? false,
  );
  let videoTitle = $state(selectedProject.video_title ?? selectedProject.title);
  let titleFont = $state(selectedProject.titleFont ?? "Hiragino Sans GB");
  let titleFontSize = $state(selectedProject.titleFontSize ?? 24);
  let titlePosition = $state(selectedProject.titlePosition ?? 50);
  // Media settings state variables
  let sortOrder = $state("alphnum");
  let keepClipLength = $state(false);
  let clipNum = $state<number | null>(null);
  // Subtitle settings state variables
  let subtitleFont = $state("Hiragino Sans GB");
  let subtitleFontSize = $state(24);
  let subtitlePosition = $state(50);
  let genSubtitle = $state(true);
  let genVoice = $state(false);
  let llmProvider = $state("qwen");
  // Audio settings state variables
  let bgmFile = $state("");
  let bgmFadeIn = $state(0.5);
  let bgmFadeOut = $state(0.5);
  let bgmVolume = $state(0.5);
  // Background music files
  let bgmFiles = $state<string[]>([]);
  let audioPlayer = $state<HTMLAudioElement | null>(null);
  let isPlaying = $state(false);

  // Load BGM files
  async function loadBgmFiles() {
    try {
      const response = await fetch("/api/media/file/public/bgm");
      if (response.ok) {
        const files = await response.json();
        bgmFiles = files.filter(
          (file: string) =>
            file.endsWith(".mp3") ||
            file.endsWith(".wav") ||
            file.endsWith(".ogg"),
        );
      } else {
        console.error("Failed to load BGM files, status:", response.status);
      }
    } catch (err) {
      console.error("Error loading BGM files:", err);
    }
  }

  // Play selected background music
  function playBgm() {
    if (!bgmFile) return;

    if (audioPlayer && isPlaying) {
      audioPlayer.pause();
      isPlaying = false;
      return;
    }

    if (audioPlayer) {
      audioPlayer.pause();
    }

    // Create new audio player
    const fullPath = `/api/media/file/public/bgm/${bgmFile}`;
    audioPlayer = new Audio(fullPath);
    audioPlayer.volume = bgmVolume;

    audioPlayer.onplay = () => {
      isPlaying = true;
    };

    audioPlayer.onpause = () => {
      isPlaying = false;
    };

    audioPlayer.onended = () => {
      isPlaying = false;
    };

    audioPlayer.play().catch((err) => {
      console.error("Error playing audio:", err);
    });
  }

  // Handle BGM file selection change
  function handleBgmChange(newBgmFile: string) {
    // If music is currently playing, stop it and play the new file
    if (audioPlayer && isPlaying) {
      audioPlayer.pause();
      isPlaying = false;

      // Update the selected file
      bgmFile = newBgmFile;

      // Play the new file
      if (bgmFile) {
        const fullPath = `/api/media/file/public/bgm/${bgmFile}`;
        audioPlayer = new Audio(fullPath);
        audioPlayer.volume = bgmVolume;

        audioPlayer.onplay = () => {
          isPlaying = true;
        };

        audioPlayer.onpause = () => {
          isPlaying = false;
        };

        audioPlayer.onended = () => {
          isPlaying = false;
        };

        audioPlayer.play().catch((err) => {
          console.error("Error playing audio:", err);
        });
      }
    } else {
      // If not playing, just update the selection
      bgmFile = newBgmFile;
    }
  }

  function startEditingTitle() {
    editedTitle = selectedProject.title;
    isEditingTitle = true;
  }

  async function saveTitle() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editedTitle,
          name: selectedProject.name,
          video_title: videoTitle,
        }),
        credentials: "include",
      });
      if (response.ok) {
        onUpdateProject({
          ...selectedProject,
          title: editedTitle,
          video_title: videoTitle,
        });
        isEditingTitle = false;
      } else {
        const errorData = await response.json();
        alert(errorData.message || "Failed to update title");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  function cancelTitle() {
    isEditingTitle = false;
  }

  async function loadContent() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        credentials: "include",
      });
      if (response.ok) {
        const project = await response.json();
        promptContent = project.prompt || "";
        staticSubtitleContent = project.staticSubtitle || "";
        onUpdateProject(project);
      } else {
        alert("Failed to load content");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  async function saveContent() {
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: selectedProject.title,
          video_title: videoTitle,
          name: selectedProject.name,
          prompt: promptContent,
          staticSubtitle: staticSubtitleContent,
          // Include title settings in save
          keepTitle,
          addTimestampToTitle,
          titleFont,
          titleFontSize,
          titlePosition,
          // Include media settings in save
          sortOrder: sortOrder,
          keepClipLength,
          clipNum: clipNum,
          // Include subtitle settings in save
          subtitleFont,
          subtitleFontSize,
          subtitlePosition,
          genSubtitle,
          genVoice,
          llmProvider,
          bgmFile,
          bgmFadeIn,
          bgmFadeOut,
          bgmVolume,
        }),
        credentials: "include",
      });
      if (response.ok) {
        onUpdateProject({
          ...selectedProject,
          prompt: promptContent,
          staticSubtitle: staticSubtitleContent,
          video_title: videoTitle,
          // Update project with new title settings
          keepTitle,
          addTimestampToTitle,
          titleFont,
          titleFontSize,
          titlePosition,
          // Update project with new media settings
          sortOrder,
          keepClipLength,
          clipNum: clipNum,
          // Update project with new subtitle settings
          subtitleFont,
          subtitleFontSize,
          subtitlePosition,
          genSubtitle,
          genVoice,
          llmProvider,
          bgmFile,
          bgmFadeIn,
          bgmFadeOut,
          bgmVolume,
        });
        console.log(selectedProject);
      } else {
        const errorData = await response.json();
        alert(errorData.message || "Failed to save content");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  async function removeMaterial(materialId: string) {
    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials?materialId=${materialId}`,
        {
          method: "DELETE",
          credentials: "include",
        },
      );
      if (response.ok) {
        loadProjectMaterials();
      } else {
        const errorData = await response.json();
        alert(errorData.message || "Failed to remove material");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  function startEditingAlias(
    materialId: string,
    currentAlias: string,
    fileName: string,
  ) {
    editingAliasId = materialId;
    if (!currentAlias || !currentAlias.trim()) {
      editingAliasValue = fileName;
    } else {
      editingAliasValue = currentAlias;
    }
  }

  async function saveAlias() {
    if (!editingAliasId || !editingAliasValue.trim()) return;

    try {
      const response = await fetch(
        `/api/projects/${selectedProject.id}/materials`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            materialId: editingAliasId,
            alias: editingAliasValue.trim(),
          }),
        },
      );

      if (response.ok) {
        const updatedMaterial = await response.json();
        // Update local state
        projectMaterials = projectMaterials.map((m: Material) =>
          m.id === editingAliasId ? updatedMaterial : m,
        );
        editingAliasId = null;
        editingAliasValue = "";
      } else {
        alert("Failed to update alias");
      }
    } catch (err) {
      alert("Network error");
      console.error(err);
    }
  }

  function cancelEditingAlias() {
    editingAliasId = null;
    editingAliasValue = "";
  }

  // Function to reset all settings to their default values
  function resetToDefaults() {
    // Video Title Settings defaults
    keepTitle = true;
    addTimestampToTitle = false;
    videoTitle = selectedProject.video_title ?? selectedProject.title;
    titleFont = "Hiragino Sans GB";
    titleFontSize = 72;
    titlePosition = 20;

    // Media Settings defaults
    sortOrder = "alphnum";
    keepClipLength = false;
    clipNum = null;

    // Subtitle Settings defaults
    subtitleFont = "Hiragino Sans GB";
    subtitleFontSize = 48;
    subtitlePosition = 80;
    genSubtitle = false;
    genVoice = false;
    llmProvider = "qwen";

    // Audio Settings defaults
    bgmFile = "";
    bgmFadeIn = 3.0;
    bgmFadeOut = 3.0;
    bgmVolume = 0.3;
  }

  // Load BGM files when component mounts
  $effect(() => {
    loadBgmFiles();
  });

  // Tab state
  let activeTab = $state("video-title");
</script>

<!-- Project Details Tab -->
<div class="space-y-6">
  <!-- Project Header -->
  <div
    class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
  >
    <div class="flex items-center justify-between">
      <div>
        {#if isEditingTitle}
          <div class="flex items-center gap-2 mb-1">
            <div>
              <label class="block text-sm font-medium text-gray-700"
                >Project Title</label
              >
              <input
                bind:value={editedTitle}
                class="text-xl font-semibold border rounded px-2 py-1 w-full"
              />
            </div>
            <button
              onclick={saveTitle}
              class="text-green-600 hover:text-green-800 self-end mb-1"
              >Save</button
            >
            <button
              onclick={cancelTitle}
              class="text-red-600 hover:text-red-800 self-end mb-1"
              >Cancel</button
            >
          </div>
        {:else}
          <div class="flex items-center gap-2 mb-1">
            <div>
              <h2 class="text-xl font-semibold">{selectedProject.title}</h2>
            </div>
            <button onclick={startEditingTitle} aria-label="Edit titles">
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                ></path>
              </svg>
            </button>
          </div>
        {/if}
        <div class="flex items-center gap-2">
          <p class="text-gray-600">{selectedProject.name}</p>
        </div>
        <!-- todo: PLACE folder relatedto AIV_VAULT_FOLDER of selectedProject here -->
      </div>
      <div class="flex gap-2">
        <button
          onclick={resetToDefaults}
          class="rounded-lg bg-gray-500 px-4 py-3 text-white transition-all duration-200 hover:bg-gray-600"
        >
          To Default
        </button>

        <div class="flex gap-2">
          <button
            onclick={loadContent}
            class="rounded-lg bg-gray-500 px-4 py-3 text-white transition-all duration-200 hover:bg-gray-600"
          >
            Reload Content
          </button>
          <button
            onclick={saveContent}
            class="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
          >
            Save Changes
          </button>
        </div>
        <button
          onclick={onGenerateVideo}
          disabled={generatingVideo}
          class="rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-3 text-white transition-all duration-200 hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {#if generatingVideo}
            <div class="flex items-center space-x-2">
              <div
                class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
              ></div>
              <span>Generating...</span>
            </div>
          {:else}
            Generate Video
          {/if}
        </button>
      </div>
    </div>
  </div>

  <!-- Project Content -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Prompt Editor -->
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold">Prompt Editor</h3>
      </div>
      prompt: {promptContent}
      <textarea
        bind:value={promptContent}
        placeholder="Enter your video generation prompt..."
        class="h-48 w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <p class="mt-2 text-sm text-gray-500">
        This prompt will be used to generate subtitles for your video.
      </p>
      <!-- Generate Subtitles -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-gray-700"
          >Generate Subtitles</label
        >
        <button
          onclick={() => (genSubtitle = !genSubtitle)}
          class={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${genSubtitle ? "bg-blue-600" : "bg-gray-200"}`}
          aria-pressed={genSubtitle}
        >
          <span
            class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${genSubtitle ? "translate-x-6" : "translate-x-1"}`}
          ></span>
        </button>
      </div>

      <!-- Generate Voice -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-gray-700">Generate Voice</label>
        <button
          onclick={() => (genVoice = !genVoice)}
          class={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${genVoice ? "bg-blue-600" : "bg-gray-200"}`}
          aria-pressed={genVoice}
        >
          <span
            class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${genVoice ? "translate-x-6" : "translate-x-1"}`}
          ></span>
        </button>
      </div>

      <!-- LLM Provider -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-gray-700">LLM Provider</label>
        <select
          bind:value={llmProvider}
          class="w-50 rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
        >
          <option value="qwen">Qwen</option>
          <option value="grok">Grok</option>
          <option value="glm">GLM</option>
          <option value="ollama">Ollama</option>
        </select>
      </div>
    </div>

    <!-- Static Subtitle -->
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <h3 class="mb-4 text-lg font-semibold">Video Title</h3>
      <div class="flex items-center justify-between">
        <input
          bind:value={videoTitle}
          class="text-xl font-semibold border rounded px-2 py-1 w-full"
        />
      </div>
      <h3 class="mt-5 mb-4 text-lg font-semibold">Static Subtitle</h3>
      <textarea
        bind:value={staticSubtitleContent}
        placeholder="Enter static subtitle text (optional)..."
        class="h-48 w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-transparent focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <p class="mt-2 text-sm text-gray-500">
        If provided, this will override the generated subtitles.
      </p>
    </div>
    <!-- Tab Navigation -->
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <div class="flex flex-wrap gap-2 mb-6">
        <button
          class={`px-4 py-2 rounded-lg transition-colors ${activeTab === "video-title" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          onclick={() => (activeTab = "video-title")}
        >
          Video Title Settings
        </button>
        <button
          class={`px-4 py-2 rounded-lg transition-colors ${activeTab === "subtitle" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          onclick={() => (activeTab = "subtitle")}
        >
          Subtitle Settings
        </button>
        <button
          class={`px-4 py-2 rounded-lg transition-colors ${activeTab === "media" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          onclick={() => (activeTab = "media")}
        >
          Media Settings
        </button>
        <button
          class={`px-4 py-2 rounded-lg transition-colors ${activeTab === "audio" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          onclick={() => (activeTab = "audio")}
        >
          Audio Settings
        </button>
      </div>

      <!-- Tab Content -->
      <div class="mt-6">
        <!-- Video Title Settings Tab -->
        {#if activeTab === "video-title"}
          <div class="space-y-4">
            <div class="space-y-4">
              <!-- Keep Title -->
              <div class="flex items-center justify-between">
                <label class="text-sm font-medium text-gray-700"
                  >Keep Title</label
                >
                <button
                  onclick={() => (keepTitle = !keepTitle)}
                  class={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${keepTitle ? "bg-blue-600" : "bg-gray-200"}`}
                  aria-pressed={keepTitle}
                >
                  <span
                    class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${keepTitle ? "translate-x-6" : "translate-x-1"}`}
                  ></span>
                </button>
              </div>

              <!-- Add Timestamp to Title -->
              <div class="flex items-center justify-between">
                <label class="text-sm font-medium text-gray-700"
                  >Add Timestamp to Title</label
                >
                <button
                  onclick={() => (addTimestampToTitle = !addTimestampToTitle)}
                  class={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${addTimestampToTitle ? "bg-blue-600" : "bg-gray-200"}`}
                  aria-pressed={addTimestampToTitle}
                >
                  <span
                    class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${addTimestampToTitle ? "translate-x-6" : "translate-x-1"}`}
                  ></span>
                </button>
              </div>

              <!-- Font Selection -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Font
                </label>
                <select
                  bind:value={titleFont}
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Hiragino Sans GB">Hiragino Sans GB</option>
                  <option value="Verdana">Verdana</option>
                  <option value="Helvetica">Helvetica</option>
                  <option value="Times New Roman">Times New Roman</option>
                  <option value="Georgia">Georgia</option>
                  <option value="Courier New">Courier New</option>
                </select>
              </div>

              <!-- Font Size -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Font Size: {titleFontSize}px
                </label>
                <input
                  type="range"
                  min="48"
                  max="100"
                  bind:value={titleFontSize}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>48</span>
                  <span>100</span>
                </div>
              </div>

              <!-- Title Position -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Title Position: {titlePosition}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  bind:value={titlePosition}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Top</span>
                  <span>Bottom</span>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Subtitle Settings Tab -->
        {#if activeTab === "subtitle"}
          <div class="space-y-4">
            <div class="space-y-4">
              <!-- Subtitle Font -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Subtitle Font
                </label>
                <select
                  bind:value={subtitleFont}
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Hiragino Sans GB">Hiragino Sans GB</option>
                  <option value="Verdana">Verdana</option>
                  <option value="Helvetica">Helvetica</option>
                  <option value="Times New Roman">Times New Roman</option>
                  <option value="Georgia">Georgia</option>
                  <option value="Courier New">Courier New</option>
                </select>
              </div>

              <!-- Subtitle Font Size -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Subtitle Font Size: {subtitleFontSize}px
                </label>
                <input
                  type="range"
                  min="48"
                  max="100"
                  bind:value={subtitleFontSize}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>48</span>
                  <span>100</span>
                </div>
              </div>

              <!-- Subtitle Position -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Subtitle Position: {subtitlePosition}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  bind:value={subtitlePosition}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Top</span>
                  <span>Bottom</span>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Media Settings Tab -->
        {#if activeTab === "media"}
          <div class="space-y-4">
            <div class="space-y-4">
              <!-- Sort Order -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Sort Order
                </label>
                <select
                  bind:value={sortOrder}
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                >
                  <option value="alphnum">Alphanumeric</option>
                  <option value="random">Random</option>
                </select>
              </div>

              <!-- Keep Clip Length -->
              <div class="flex items-center justify-between">
                <label class="text-sm font-medium text-gray-700"
                  >Keep Clip Length</label
                >
                <button
                  onclick={() => (keepClipLength = !keepClipLength)}
                  class={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${keepClipLength ? "bg-blue-600" : "bg-gray-200"}`}
                  aria-pressed={keepClipLength}
                >
                  <span
                    class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${keepClipLength ? "translate-x-6" : "translate-x-1"}`}
                  ></span>
                </button>
              </div>

              <!-- Number of Clips -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Number of Clips
                </label>
                <input
                  type="number"
                  bind:value={clipNum}
                  placeholder="Auto"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        {/if}

        <!-- Audio Settings Tab -->
        {#if activeTab === "audio"}
          <div class="space-y-4">
            <div class="space-y-4">
              <!-- BGM File Selector -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Background Music File
                </label>
                <div class="flex gap-2">
                  <select
                    value={bgmFile}
                    onchange={(e) => {
                      const target = e.target as HTMLSelectElement;
                      handleBgmChange(target.value);
                    }}
                    class="flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">None</option>
                    {#each bgmFiles as file}
                      <option value={file}>{file}</option>
                    {/each}
                  </select>
                  <button
                    onclick={playBgm}
                    class="flex items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    disabled={!bgmFile}
                    aria-label={isPlaying
                      ? "Stop playback"
                      : "Play selected music"}
                  >
                    <svg
                      class="h-5 w-5"
                      fill={isPlaying ? "currentColor" : "none"}
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      {#if isPlaying}
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M10 9v6m4-6v6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                        ></path>
                      {:else}
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                        ></path>
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        ></path>
                      {/if}
                    </svg>
                  </button>
                </div>
              </div>

              <!-- BGM Fade In -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  BGM Fade In (seconds): {bgmFadeIn}
                </label>
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="0.1"
                  bind:value={bgmFadeIn}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>5</span>
                </div>
              </div>

              <!-- BGM Fade Out -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  BGM Fade Out (seconds): {bgmFadeOut}
                </label>
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="0.1"
                  bind:value={bgmFadeOut}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>5</span>
                </div>
              </div>

              <!-- BGM Volume -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  BGM Volume: {bgmVolume}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  bind:value={bgmVolume}
                  class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div class="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>1</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Materials Management -->
  <div
    class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
  >
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold">Project Materials</h3>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {#if loadingMaterials}
        <div class="col-span-full flex items-center justify-center py-8">
          <div class="flex items-center space-x-2">
            <div
              class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
            ></div>
            <span>Loading materials...</span>
          </div>
        </div>
      {:else if projectMaterials.length === 0}
        <div class="col-span-full text-center py-8 text-gray-500">
          <div class="text-gray-400 mb-2">
            <svg
              class="mx-auto h-12 w-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              ></path>
            </svg>
          </div>
          <p>No materials added to this project yet</p>
          <p class="text-sm mt-1">
            Click "Manage Materials" to add files from your media library
          </p>
        </div>
      {:else}
        {#each sortedProjectMaterials as material (material.id)}
          {@const url = `/api/media/file/${material.relativePath.split("/")[0] === "public" ? "public" : "user"}/${material.relativePath.split("/").slice(2).join("/")}`}
          <div
            class="group relative w-full overflow-hidden rounded-lg border-2 border-gray-200 bg-white transition-all hover:shadow-md"
          >
            <button
              onclick={() => removeMaterial(material.id)}
              class="absolute top-2 right-2 z-10 rounded-full bg-red-500 p-1 text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              aria-label="Remove material"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            {#if material.fileType === "image"}
              <div class="relative">
                <button
                  type="button"
                  class="w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  onclick={() =>
                    onPreviewMedia({
                      type: "image",
                      url,
                      name: material.fileName,
                    })}
                  aria-label={`Preview ${material.fileName}`}
                >
                  <div class="aspect-square overflow-hidden bg-gray-100">
                    <img
                      src={url}
                      alt={material.fileName}
                      class="h-full w-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                </button>
              </div>
            {:else if material.fileType === "video"}
              <div class="relative">
                <button
                  type="button"
                  class="w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  onclick={() =>
                    onPreviewMedia({
                      type: "video",
                      url,
                      name: material.fileName,
                    })}
                  aria-label={`Preview ${material.fileName}`}
                >
                  <div
                    class="aspect-square overflow-hidden bg-gray-100 relative"
                  >
                    <video
                      src={url}
                      class="h-full w-full object-cover"
                      muted
                      preload="metadata"
                      onloadedmetadata={(e) =>
                        ((e.target as HTMLVideoElement).currentTime = 0)}
                    ></video>
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-transparent bg-opacity-20"
                    >
                      <div class="rounded-full bg-white bg-opacity-80 p-2">
                        <svg
                          class="h-6 w-6 text-gray-700"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            {:else}
              <div
                class="aspect-square flex items-center justify-center bg-gray-100 rounded-lg relative"
              >
                <span class="text-4xl">{getMediaIcon(material.fileType)}</span>
              </div>
            {/if}

            <div class="p-2">
              <p
                class="truncate text-xs font-medium text-gray-900"
                title={material.fileName}
              >
                {material.fileName}
              </p>
              {#if editingAliasId === material.id}
                <input
                  bind:value={editingAliasValue}
                  onkeydown={(e) => {
                    if (e.key === "Enter") saveAlias();
                    if (e.key === "Escape") cancelEditingAlias();
                  }}
                  onblur={saveAlias}
                  class="w-full text-center border-1 outline-none"
                />
              {:else}
                <span
                  role="button"
                  tabindex="0"
                  onclick={() =>
                    startEditingAlias(
                      material.id,
                      material.alias,
                      material.fileName,
                    )}
                  onkeydown={(e) => {
                    if (e.key === "Enter") {
                      startEditingAlias(
                        material.id,
                        material.alias,
                        material.fileName,
                      );
                    }
                  }}>{material.alias ?? "edit alias"}</span
                >
              {/if}
              <p class="text-xs text-gray-500">{material.fileType}</p>
              <p class="text-xs text-gray-400">
                {new Date(material.createdAt).toLocaleDateString()}
              </p>
            </div>
          </div>
        {/each}
        <div
          class="group relative w-full overflow-hidden rounded-lg border-2 border-gray-200 bg-white transition-all hover:shadow-md flex items-center justify-center"
        >
          <button
            class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600 flex flex-col items-center"
            onclick={() => onShowMaterialsModal(() => loadProjectMaterials())}
          >
            <svg
              class="h-12 w-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              ></path>
            </svg>
            <span class="mt-2">Manage Materials</span>
          </button>
        </div>
      {/if}
    </div>
  </div>

  <!-- Logs -->
  {#if showLogs}
    <div
      class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
    >
      <h3 class="mb-4 text-lg font-semibold">Generation Logs</h3>
      <div class="h-48 overflow-auto rounded-lg bg-gray-900 p-4">
        <pre class="text-sm text-green-400 font-mono">{generationLogs}</pre>
      </div>
    </div>
  {/if}
</div>
