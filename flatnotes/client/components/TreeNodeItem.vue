<template>
  <!-- Folder -->
  <div v-if="node.type === 'folder'">
    <button
      class="flex w-full items-center gap-1 rounded px-2 py-1 text-left text-sm text-theme-text hover:bg-theme-background-elevated"
      @click="open = !open"
    >
      <svg
        class="h-4 w-4 shrink-0 text-theme-text-muted transition-transform"
        :class="{ 'rotate-90': open }"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M8 5l8 7-8 7V5z" />
      </svg>
      <svg
        class="h-4 w-4 shrink-0 text-theme-brand"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path
          v-if="open"
          d="M19 20H4a2 2 0 01-2-2V6a2 2 0 012-2h6l2 2h7a2 2 0 012 2v10a2 2 0 01-2 2z"
        />
        <path
          v-else
          d="M20 6h-8l-2-2H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2z"
        />
      </svg>
      <span class="truncate font-medium">{{ node.name }}</span>
    </button>
    <div v-show="open" class="ml-4 border-l border-theme-border pl-1">
      <TreeNodeItem
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :activeNotePath="activeNotePath"
        @navigate="$emit('navigate', $event)"
      />
    </div>
  </div>

  <!-- File -->
  <button
    v-else
    class="flex w-full items-center gap-1 rounded px-2 py-1 text-left text-sm"
    :class="
      activeNotePath === node.path
        ? 'bg-theme-brand/20 font-semibold text-theme-text'
        : 'text-theme-text-muted hover:bg-theme-background-elevated hover:text-theme-text'
    "
    @click="$emit('navigate', node.path)"
  >
    <svg
      class="h-4 w-4 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
      />
    </svg>
    <span class="truncate">{{ node.name }}</span>
  </button>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  node: { type: Object, required: true },
  activeNotePath: { type: String, default: null },
});

defineEmits(["navigate"]);

// Folders start open if they contain the active note
const containsActive = (node, activePath) => {
  if (!activePath || node.type === "file") return false;
  return (node.children || []).some(
    (c) => c.path === activePath || containsActive(c, activePath),
  );
};

const open = ref(containsActive(props.node, props.activeNotePath));
</script>
