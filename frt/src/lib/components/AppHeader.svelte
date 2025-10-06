<script lang="ts">
  interface User {
    id: string;
    username: string;
  }

  export let checkingAuth: boolean;
  export let user: User | null;
  export let onLogout: () => void;
  export let onShowAuth: () => void;
</script>

<header
  class="sticky top-0 z-50 border-b border-gray-200/50 bg-white/80 backdrop-blur-md"
>
  <div class="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between">
      <h1
        class="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-2xl font-bold text-transparent"
      >
        AI Video Content Manager
      </h1>

      {#if checkingAuth}
        <div class="flex items-center gap-4">
          <div
            class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
          ></div>
          <span class="text-sm text-gray-600">Checking session...</span>
        </div>
      {:else if user}
        <div class="flex items-center gap-4">
          <span class="text-sm text-gray-600">Welcome, {user.username}</span>
          <button
            on:click={onLogout}
            class="rounded-lg bg-red-500 px-4 py-2 text-white transition-colors hover:bg-red-600"
          >
            Logout
          </button>
        </div>
      {:else}
        <button
          on:click={onShowAuth}
          class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600"
        >
          Login
        </button>
      {/if}
    </div>
  </div>
</header>
