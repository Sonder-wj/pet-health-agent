<template>
  <div class="thinking-indicator">
    <div class="avatar-pulse">
      <svg viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="12" r="7" fill="var(--amber-100)" stroke="var(--amber-400)" stroke-width="1.2"/>
        <circle cx="12" cy="9" r="1.2" fill="var(--amber-600)"/>
        <circle cx="20" cy="9" r="1.2" fill="var(--amber-600)"/>
        <ellipse cx="16" cy="13" rx="2" ry="1" fill="var(--amber-500)"/>
      </svg>
    </div>
    <div class="dots-row">
      <span class="dot" />
      <span class="dot" />
      <span class="dot" />
    </div>
  </div>
</template>

<style scoped>
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  animation: think-in var(--duration-normal) var(--ease-out);
}
@keyframes think-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.avatar-pulse {
  width: 36px; height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: breathe 2s ease-in-out infinite;
}
.avatar-pulse svg {
  width: 32px; height: 32px;
}
@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.08); opacity: 1; }
}

.dots-row {
  display: flex;
  gap: 5px;
}
.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--amber-400);
  animation: dot-bounce 1.2s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-6px); opacity: 1; }
}
</style>
