<template>
  <div class="profile-card">
    <div class="card-header">
      <h3>🐾 宠物档案</h3>
      <span v-if="!hasData" class="hint">营养师对话中会逐步收集</span>
    </div>

    <div v-if="hasData" class="fields">
      <div v-if="profile.species" class="field">
        <span class="key">物种</span>
        <span class="val">{{ speciesLabel }}</span>
      </div>
      <div v-if="profile.weight_kg" class="field">
        <span class="key">体重</span>
        <span class="val">{{ profile.weight_kg }} kg</span>
      </div>
      <div v-if="profile.age_months !== undefined" class="field">
        <span class="key">月龄</span>
        <span class="val">{{ profile.age_months }} 月</span>
      </div>
      <div v-if="profile.neutered !== undefined" class="field">
        <span class="key">是否绝育</span>
        <span class="val">{{ profile.neutered ? '是' : '否' }}</span>
      </div>
      <div v-if="profile.conditions?.length" class="field">
        <span class="key">健康状况</span>
        <span class="val tags">
          <span v-for="c in profile.conditions" :key="c" class="tag warn">{{ c }}</span>
        </span>
      </div>
      <div v-if="profile.allergens?.length" class="field">
        <span class="key">已知过敏</span>
        <span class="val tags">
          <span v-for="a in profile.allergens" :key="a" class="tag danger">{{ a }}</span>
        </span>
      </div>
    </div>

    <div v-else class="empty">
      <p>开始对话后,这里会展示已收集到的宠物信息。</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  profile: { type: Object, default: () => ({}) },
})

const hasData = computed(() => {
  const p = props.profile || {}
  return !!(p.species || p.weight_kg || p.age_months !== undefined ||
            p.neutered !== undefined || p.conditions?.length || p.allergens?.length)
})

const speciesLabel = computed(() => {
  const map = { dog: '🐕 狗', cat: '🐈 猫' }
  return map[props.profile?.species] || props.profile?.species
})
</script>

<style scoped>
.profile-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-header h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  color: var(--text-primary);
}

.hint {
  font-size: 11px;
  color: var(--text-secondary);
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.key {
  color: var(--text-secondary);
}

.val {
  color: var(--text-primary);
  font-weight: 500;
}

.tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
}

.tag.warn {
  background: var(--amber-100);
  color: var(--amber-700);
}

.tag.danger {
  background: var(--red-100);
  color: var(--red-700);
}

.empty {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
  padding: 8px 0;
}
</style>
