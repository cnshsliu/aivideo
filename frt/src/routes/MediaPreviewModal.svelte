<script lang="ts">
  export let previewMedia: {
    type: 'image' | 'video';
    url: string;
    name: string;
    poster?: string;
  } | null;
  export let onClose: () => void;

  let modalDiv: HTMLDivElement;

  $: if (previewMedia && modalDiv) {
    modalDiv.focus();
  }
</script>

{#if previewMedia}
  <div
    class="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    bind:this={modalDiv}
    on:keydown={(e) => {
      if (e.key === 'Escape') onClose();
    }}
  >
    <div class="relative max-w-4xl max-h-[90vh] w-full mx-4">
      <!-- Close button -->
      <button
        on:click={onClose}
        class="absolute top-4 right-4 z-10 text-white bg-black bg-opacity-50 rounded-full p-2 hover:bg-opacity-70 transition-all duration-200"
        aria-label="Close preview"
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

      <!-- Media display -->
      {#if previewMedia.type === 'image'}
        <img
          src={previewMedia.url}
          alt={previewMedia.name}
          class="w-full h-auto max-h-[80vh] object-contain rounded-lg"
        />
      {:else if previewMedia.type === 'video'}
        <video
          controls
          class="w-full h-auto max-h-[80vh] rounded-lg"
          poster={previewMedia.poster}
        >
          <source src={previewMedia.url} type="video/mp4" />
          <track kind="captions" src="" srclang="en" label="No captions" />
          Your browser does not support the video tag.
        </video>
      {/if}

      <!-- Media info -->
      <div class="mt-4 text-center">
        <p class="text-white text-lg font-medium">{previewMedia.name}</p>
      </div>
    </div>
  </div>
{/if}
