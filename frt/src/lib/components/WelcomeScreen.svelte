<script lang="ts">
  export let onGetStarted: () => void;
</script>

<!-- Welcome Screen for Unauthenticated Users -->
<div class="text-center py-12">
  <h2 class="text-3xl font-bold text-gray-900 mb-4">
    Welcome to AI Video Content Manager
  </h2>
  <p class="text-xl text-gray-600 mb-8">
    Create stunning videos from your media with AI-powered content generation
  </p>
  <button
    on:click={onGetStarted}
    class="rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 px-8 py-4 text-lg text-white transition-all duration-200 hover:from-blue-600 hover:to-purple-600"
  >
    Get Started
  </button>
</div>
