/**
 * 杀手组织老板模拟器 v2 — 前端逻辑
 *
 * 纯按钮操作，无文本输入框。
 * 所有动作通过 POST /api/act 与后端交互。
 */

// ============================================================
// 状态
// ============================================================

const API_BASE = window.location.origin;

let STATE = null;
let gameStarted = false;
let loading = false;
let modalState = null;
let currentContractIndex = null;

// ============================================================
// DOM 引用
// ============================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Header
    dayBadge: $('#day-badge'),
    orgBadge: $('#org-badge'),
    headerFunds: $('#header-funds'),
    headerRep: $('#header-rep'),
    headerAp: $('#header-ap'),

    // Stats panel
    statFunds: $('#stat-funds'),
    statRep: $('#stat-rep'),
    statRepBar: $('#rep-bar-fill'),
    statApDots: $('#ap-dots'),
    statDay: $('#stat-day'),

    // Narrative
    narrativeContent: $('#narrative-content'),

    // Hitman
    hitmanList: $('#hitman-list'),
    hitmanCount: $('#hitman-count'),

    // Buttons
    btnStart: $('#btn-start'),
    btnContracts: $('#btn-contracts'),
    btnRecruit: $('#btn-recruit'),
    btnDevelop: $('#btn-develop'),
    btnFactions: $('#btn-factions'),
    btnLeaderboard: $('#btn-leaderboard'),
    btnRivals: $('#btn-rivals'),
    btnWeaponShop: $('#btn-weapon-shop'),
    btnTraining: $('#btn-training'),
    btnEndDay: $('#btn-end-day'),
    btnSave: $('#btn-save'),
    btnLoad: $('#btn-load'),
    btnRestart: $('#btn-restart'),
    resetLink: $('#reset-link'),

    // Screens
    startScreen: $('#start-screen'),
    gameUI: $('#game-ui'),

    // Modal
    modalOverlay: $('#modal-overlay'),
    modalHeader: $('#modal-header'),
    modalBody: $('#modal-body'),
    modalClose: $('#modal-close'),

    // Loading
    loadingOverlay: $('#loading-overlay'),
    loadingText: $('#loading-text'),

    // Hitman detail
    hitmanDetail: $('#hitman-detail'),
};

// ============================================================
// API 调用
// ============================================================

const TIMEOUT_MS = 25000;

async function fetchWithTimeout(url, options, timeoutMs) {
    timeoutMs = timeoutMs || TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(url, { ...options, signal: controller.signal });
        return resp;
    } finally {
        clearTimeout(timer);
    }
}

async function apiCall(action, params = {}) {
    if (loading) return null;
    setLoading(true);
    try {
        const resp = await fetchWithTimeout(`${API_BASE}/api/act`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, params }),
        });
        if (!resp.ok) {
            const errText = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${errText}`);
        }
        const data = await resp.json();
        return data;
    } catch (err) {
        console.error('API call failed:', err);
        if (err.name === 'AbortError') {
            appendNarrative('⚠️ 请求超时，请检查网络后重试。', 'system');
        } else {
            appendNarrative(`⚠️ 通讯中断：${err.message}`, 'system');
        }
        return null;
    } finally {
        setLoading(false);
    }
}

async function apiStart() {
    if (loading) return null;
    setLoading(true);
    try {
        const resp = await fetchWithTimeout(`${API_BASE}/api/start`, { method: 'POST' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data;
    } catch (err) {
        console.error('Start failed:', err);
        if (err.name === 'AbortError') {
            appendNarrative('⚠️ 请求超时，请检查网络后重试。', 'system');
        }
        return null;
    } finally {
        setLoading(false);
    }
}

// ============================================================
// 渲染
// ============================================================

function updateStats(state) {
    STATE = state;

    // Header
    dom.dayBadge.textContent = `第 ${state.day} 天`;
    dom.orgBadge.textContent = `Lv.${state.org_level} ${state.org_level_name}`;
    dom.headerFunds.textContent = formatMoney(state.funds);
    dom.headerRep.textContent = `${state.reputation}/${state.max_reputation}`;
    dom.headerAp.textContent = `${state.ap}/${state.max_ap}`;

    // Stats panel
    dom.statFunds.textContent = formatMoney(state.funds);
    dom.statRep.textContent = `${state.reputation}`;
    dom.statRepBar.style.width = `${(state.reputation / state.max_reputation) * 100}%`;

    // AP dots
    dom.statApDots.innerHTML = '';
    for (let i = 0; i < state.max_ap; i++) {
        const dot = document.createElement('div');
        dot.className = `ap-dot ${i < state.ap ? 'filled' : 'empty'}`;
        dom.statApDots.appendChild(dot);
    }

    dom.statDay.textContent = `第 ${state.day} 天`;

    // Hitmen
    renderHitmen(state.hitmen);

    // Buttons
    updateButtons(state);
}

function renderHitmen(hitmen) {
    dom.hitmanList.innerHTML = '';

    if (!hitmen || hitmen.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'hitman-card empty';
        empty.textContent = '🔫 暂无杀手，去招募吧';
        dom.hitmanList.appendChild(empty);
        dom.hitmanCount.textContent = '0';
        return;
    }

    dom.hitmanCount.textContent = hitmen.length;

    hitmen.forEach((h) => {
        const card = document.createElement('div');
        card.className = 'hitman-card';
        card.dataset.id = h.id;

        const weaponName = h.weapon_id ? state.weapons?.find(w => w.id === h.weapon_id)?.name || '' : '';
        const lv = h.lv || 1;
        const exp = h.exp || 0;
        const needExp = lv * 50;

        // Legend title (Lv8 unlock)
        const legend = h.legend_title ? ` [${h.legend_title}]` : '';

        card.innerHTML = `
            <div class="name">
                ${h.name}${legend}
                <span class="spec-badge">${h.specialty}</span>
            </div>
            <div class="details">
                <span>⚔️ Lv.${lv}</span>
                <span>💪 ${h.skill}</span>
                <span>📊 ${Math.round((h.cut||0.2)*100)}%抽</span>
            </div>
            <div class="details" style="font-size:10px;color:#888;">
                ${weaponName ? '🔫 '+weaponName : ''}
                <span>❤️${h.loyalty}</span>
                <span>EXP ${exp}/${needExp}</span>
            </div>
            <span class="status-badge ${h.status}">${statusText(h.status)}</span>
        `;

        card.addEventListener('click', () => showHitmanDetail(h, card));
        dom.hitmanList.appendChild(card);
    });
}

function statusText(status) {
    const map = { idle: '空闲', injured: '受伤', on_mission: '任务中', dead: '死亡' };
    return map[status] || status;
}

function updateButtons(state) {
    const apOk = state.ap > 0;
    const hasHitmen = (state.hitmen || []).length > 0;

    dom.btnRecruit.disabled = !gameStarted || state.game_over || !apOk;
    dom.btnContracts.disabled = !gameStarted || state.game_over;
    dom.btnWeaponShop.disabled = !gameStarted || state.game_over;
    dom.btnLeaderboard.disabled = !gameStarted;
    dom.btnSave.disabled = !gameStarted || state.game_over;
    dom.btnLoad.disabled = !gameStarted || state.game_over;
    dom.btnTraining.disabled = !gameStarted || state.game_over || !apOk || !hasHitmen;
    dom.btnRivals.disabled = !gameStarted || state.game_over;
    dom.btnEndDay.disabled = !gameStarted || state.game_over;
    dom.btnDevelop.disabled = !gameStarted || state.game_over;
    dom.btnFactions.disabled = !gameStarted || state.game_over || state.org_level < 4;
}

function appendNarrative(text, type = 'narrative') {
    const msg = document.createElement('div');
    msg.className = `narrative-msg ${type}`;
    msg.textContent = text;
    dom.narrativeContent.appendChild(msg);
    dom.narrativeContent.scrollTop = dom.narrativeContent.scrollHeight;
}

function clearNarrative() {
    dom.narrativeContent.innerHTML = '';
}

// --- Toast ---
function showToast(msg, durationMs) {
    durationMs = durationMs || 2000;
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 24px;border-radius:8px;font-size:14px;z-index:9999;opacity:0;transition:opacity 0.3s;pointer-events:none;';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, durationMs);
}

// ============================================================
// Modal 系统
// ============================================================

function showModal(title, contentHtml) {
    dom.modalHeader.innerHTML = `<h2>${title}</h2>`;
    dom.modalBody.innerHTML = contentHtml;
    dom.modalOverlay.classList.remove('hidden');
    dom.modalClose.onclick = closeModal;
    dom.modalOverlay.onclick = (e) => {
        if (e.target === dom.modalOverlay) closeModal();
    };
}

function closeModal() {
    dom.modalOverlay.classList.add('hidden');
    modalState = null;
    setLoading(false);
}

// ============================================================
// 操作处理
// ============================================================

// --- 开始游戏 ---
async function handleStart() {
    const data = await apiStart();
    if (!data) return;

    dom.startScreen.classList.add('hidden');
    dom.gameUI.classList.remove('hidden');

    gameStarted = true;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');
    setLoading(false);

    // 检查主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 300);
    }
}

// --- 主线剧情 ---
function showMainStoryModal(story) {
    let html = `<div style="margin-bottom:16px;line-height:1.8;">${story.text.replace(/\n/g, '<br>')}</div>`;
    html += '<div style="display:flex;flex-direction:column;gap:8px;">';
    story.choices.forEach((choice, i) => {
        html += `<button class="btn btn-gold" onclick="doResolveStory(${story.level}, ${i})" style="width:100%;">${choice.text}</button>`;
    });
    html += '</div>';
    showModal(`📖 ${story.title}`, html);
}

async function doResolveStory(level, choiceIndex) {
    closeModal();
    const data = await apiCall('resolve_story', { level, choice_index: choiceIndex });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    if (data.extra?.ending) {
        appendNarrative(`🎬 结局达成：${data.extra.ending}`, 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

// --- 契约板 ---
async function handleShowContracts() {
    modalState = 'contracts';
    const data = await apiCall('contracts');
    if (!data) return;

    const contracts = data.extra?.contracts || [];
    if (contracts.length === 0) {
        showModal('📋 契约板', '<p style="color:var(--text-muted)">今天的契约板是空的……</p>');
        return;
    }

    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择要执行的契约：</p>';
    contracts.forEach((c, idx) => {
        const diffClass = { '简单': 'easy', '中等': 'medium', '困难': 'hard', '致命': 'fatal' }[c.difficulty] || 'medium';
        html += `
            <div class="contract-card" data-index="${idx}">
                <div class="contract-title">
                    <span>${c.name}</span>
                    <span class="contract-diff ${diffClass}">${c.difficulty}</span>
                </div>
                <div class="contract-meta">
                    <span>🎯 ${c.required_specialty}</span>
                    <span>⭐ 要求: ${c.reputation_req}</span>
                    <span>💰 ${formatMoney(c.reward)}</span>
                </div>
                <div class="contract-action">
                    <button class="btn btn-gold btn-sm" onclick="handleAssignContract(${idx})">派遣杀手 ➤</button>
                </div>
            </div>
        `;
    });

    showModal('📋 契约板', html);
    setLoading(false);
}

// --- 派遣杀手 + 方案选择 ---
async function handleAssignContract(contractIndex) {
    modalState = 'assign';
    const hitmen = STATE?.hitmen || [];
    const idleHitmen = hitmen.filter(h => h.status === 'idle');

    if (idleHitmen.length === 0) {
        appendNarrative('没有空闲的杀手可以派遣。', 'system');
        closeModal();
        return;
    }

    currentContractIndex = contractIndex;
    const contract = STATE.contracts[contractIndex];
    const orgLevel = STATE.org_level;

    let html = `<p style="margin-bottom:12px;color:var(--text-secondary);">
        契约：<strong>${contract.name}</strong>（${contract.difficulty} · ${contract.required_specialty}）
    </p>
    <p style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">选择派遣的杀手：</p>`;

    const sorted = [...idleHitmen].sort((a, b) => {
        const aMatch = a.specialty === contract.required_specialty ? -1 : 1;
        const bMatch = b.specialty === contract.required_specialty ? -1 : 1;
        return aMatch - bMatch;
    });

    sorted.forEach(h => {
        const isMatch = h.specialty === contract.required_specialty;
        html += `
            <div class="hitman-select-card" onclick="showPlanChoice(${contractIndex}, ${h.id})">
                <div>
                    <span class="sel-name">${h.name}</span>
                    <span class="sel-spec ${isMatch ? 'match' : ''}">
                        ${h.specialty} ${isMatch ? '✓' : ''}
                    </span>
                </div>
                <div style="font-size:12px;color:var(--text-muted);">
                    ⚔️ Lv.${h.skill} · ❤️${h.loyalty}
                </div>
            </div>
        `;
    });

    dom.modalBody.innerHTML = html;
}

async function showPlanChoice(contractIndex, hitmanId) {
    // Lv3以下直接执行
    if (STATE.org_level < 3) {
        await executeAssign(contractIndex, hitmanId, null);
        return;
    }

    // 获取可用方案
    const data = await apiCall('contract_plans', { hitman_id: hitmanId, contract_index: contractIndex });
    if (!data) return;

    const plans = data.extra?.plans || [];
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择执行方案（Lv.3解锁）：</p>';

    // 标准方案
    html += `
        <div class="candidate-card" onclick="executeAssign(${contractIndex}, ${hitmanId}, null)" style="cursor:pointer;margin-bottom:6px;">
            <div><strong>标准执行</strong></div>
            <div style="font-size:12px;color:var(--text-muted);">按常规方式执行，收益正常</div>
        </div>
    `;

    plans.forEach(p => {
        const avClass = p.is_available ? '' : 'style="opacity:0.5;"';
        html += `
            <div class="candidate-card" onclick="${p.is_available ? `executeAssign(${contractIndex}, ${hitmanId}, '${p.id}')` : 'showToast(\'专长不匹配\')'}" ${avClass} style="cursor:${p.is_available ? 'pointer' : 'not-allowed'};margin-bottom:6px;">
                <div><strong>${p.name}</strong> ${p.is_available ? '<span style="color:var(--accent-green);font-size:11px;">✓ 匹配</span>' : '<span style="color:var(--text-muted);font-size:11px;">✗ 专长不匹配</span>'}</div>
                <div style="font-size:12px;color:var(--text-muted);">${p.desc}</div>
            </div>
        `;
    });

    showModal('🎯 选择方案', html);
    setLoading(false);
}

async function executeAssign(contractIndex, hitmanId, planId) {
    closeModal();
    closeModal(); // 关闭方案选择 + 契约板
    closeModal();
    const data = await apiCall('assign_contract', {
        contract_index: contractIndex,
        hitman_id: hitmanId,
        plan_id: planId,
    });
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    // 主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 300);
    }

    if (data.state.game_over) {
        appendNarrative('☠️ 游戏结束。这座城市的暗面永远在吞噬弱者。', 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

// --- 招募 ---
async function handleRecruit() {
    modalState = 'recruit';
    const data = await apiCall('recruit');
    if (!data) return;

    if (data.error) {
        appendNarrative(data.error, 'system');
        closeModal();
        return;
    }

    const candidates = data.extra?.candidates || [];
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">今天来应聘的杀手：</p>';

    candidates.forEach((c, idx) => {
        html += `
            <div class="candidate-card" onclick="handleHire(${idx})">
                <div class="cand-name">
                    ${c.name}
                    <span style="font-size:12px;color:var(--text-muted);font-weight:400;">
                        ${c.specialty}
                    </span>
                </div>
                <div class="cand-stats">
                    <span>⚔️ 战力 ${c.skill}/5</span>
                    <span>❤️ 忠诚 ${c.loyalty}/10</span>
                    <span>📊 抽成 ${Math.round((c.cut||0.2)*100)}%</span>
                </div>
                <div class="cand-cost">
                    💸 招募费：${formatMoney(c.recruitment_cost)}
                </div>
            </div>
        `;
    });

    showModal('👤 招募新杀手', html);
    setLoading(false);
}

async function handleHire(candidateIndex) {
    closeModal();
    const data = await apiCall('hire', { candidate_index: candidateIndex });
    if (!data) return;

    if (data.extra?.hired === false) {
        appendNarrative(data.narrative, 'system');
    } else {
        updateStats(data.state);
        appendNarrative(data.narrative, 'narrative');
    }
    setLoading(false);
}

// --- 解雇杀手 ---
function handleFireHitman(hitmanId) {
    if (!confirm('确定要解雇这名杀手吗？')) return;
    apiCallAndRefresh('fire', { hitman_id: hitmanId });
}

// --- 装备/卸下武器 ---
async function doEquipWeapon(hitmanId, weaponId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('equip_weapon', { hitman_id: hitmanId, weapon_id: weaponId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state);
}

async function doUnequipWeapon(hitmanId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('unequip_weapon', { hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state);
}

// --- 结束今天 ---
async function handleEndDay() {
    const data = await apiCall('end_day');
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    // 街头偶遇
    const enc = data.extra?.encounter;
    if (enc && enc.name) {
        const canAfford = data.state.funds >= enc.cost && data.state.ap > 0;
        showModal('✨ 街头偶遇',
            '你在街头遇到了一个有意思的人：<br><br>' +
            '<b>' + enc.name + '</b>(' + enc.specialty + '，战力' + enc.skill + ')<br>' +
            '招募费用：¥' + enc.cost + '<br><br>' +
            (canAfford
                ? '<button class="btn btn-primary" onclick="doPickupEncounter()" style="margin-right:8px">❤ 招募</button>'
                : '<span style="color:#f87171;">' + (data.state.funds < enc.cost ? '资金不足' : '行动力不足') + '</span>'
            ) +
            '<button class="btn" onclick="closeModal()">❌ 忽略</button>'
        );
    }

    // 组织升级
    if (data.extra?.upgrade) {
        const up = data.extra.upgrade;
        appendNarrative(`⬆️ 组织晋升！${up.new_name}（Lv.${up.new_level}）`, 'event');
    }

    // 主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 500);
    }

    if (data.state.game_over) {
        appendNarrative('☠️ 游戏结束。这座城市又吞掉了一个组织。', 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

async function doPickupEncounter() {
    closeModal();
    const data = await apiCall('pickup');
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');
}

async function handleSave() {
    const slot = 1;
    const data = await apiCall('save', { slot });
    if (!data) return;
    let msg = data.narrative || `💾 存档已保存（第${slot}栏）`;
    appendNarrative(msg, 'narrative');
    showToast('存档成功 ✅');
    setLoading(false);
}

async function handleLoad() {
    const savesResp = await apiCall('list_saves');
    if (!savesResp) return;
    const saves = savesResp.extra?.saves || [];
    if (saves.length === 0) {
        showToast('没有找到存档 ❌');
        setLoading(false);
        return;
    }
    const slot = 1;
    const data = await apiCall('load', { slot });
    if (!data) return;
    updateUI(data.state, data.narrative);
    setLoading(false);
}

async function handleRestart() {
    dom.btnRestart.classList.add('hidden');
    await handleStart();
}

// --- 竞争对手 ---
async function handleRivals() {
    modalState = 'rivals';
    const data = await apiCall('rivals');
    if (!data) return;
    closeModal();
    const rivals = data.extra?.rivals || [];
    const idleHitmen = (data.state.hitmen || []).filter(h => h.status === 'idle');
    let html = '<div id="rival-modal-content">';
    rivals.forEach(r => {
        const hostilityBar = '\uD83D\uDD34'.repeat(Math.ceil(r.hostile / 20)).padEnd(5, '\u26AA');
        html += '<div style="border:1px solid #c0392b;border-radius:8px;padding:10px;margin-bottom:8px;background:#221111;" data-rival-id="' + r.id + '">';
        html += '<div style="font-weight:bold;color:#e74c3c;">' + r.name + '</div>';
        html += '<div style="font-size:12px;color:#888;">\uD83D\uDCAA战力' + r.strength + ' \u00B7 \uD83C\uDFE0' + r.territory + '街区 \u00B7 \u2B50声望' + r.reputation + '</div>';
        html += '<div style="font-size:11px;color:#666;">敌意: ' + hostilityBar + '</div>';
        if (idleHitmen.length > 0 && data.state.ap > 0) {
            html += '<div style="margin-top:4px;font-size:11px;color:#aaa;">勾选要派出的杀手:</div><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">';
            idleHitmen.forEach(h => {
                html += '<label style="border:1px solid #555;border-radius:6px;padding:4px 8px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;">';
                html += '<input type="checkbox" class="rival-hitman-cb" data-rival-id="' + r.id + '" data-hitman-id="' + h.id + '" style="accent-color:#e74c3c;">';
                html += h.name + '</label>';
            });
            html += '</div>';
            html += '<button class="btn btn-sm btn-danger" onclick="doMultiAttackRival(' + r.id + ')" style="margin-top:6px;width:100%;">\u2694\uFE0F 集体出击</button>';
        }
        html += '</div>';
    });
    html += '</div>';
    showModal('\u2694\uFE0F 竞争对手', html || '<p style="color:#888;">城里已经没有活着的对手了。</p>');
}

async function doMultiAttackRival(rivalId) {
    const checkboxes = document.querySelectorAll('.rival-hitman-cb[data-rival-id="' + rivalId + '"]:checked');
    const hitmanIds = Array.from(checkboxes).map(cb => parseInt(cb.dataset.hitmanId));
    if (hitmanIds.length === 0) {
        showToast('请至少勾选一个杀手');
        return;
    }
    closeModal();
    const data = await apiCall('attack_rival', { rival_id: rivalId, hitman_ids: hitmanIds });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 武器库 ---
async function handleWeaponShop() {
    modalState = 'weapon_shop';
    const data = await apiCall('weapon_shop');
    if (!data) return;
    closeModal();
    const weapons = data.extra?.weapons || [];
    if (weapons.length === 0) {
        appendNarrative(data.narrative, 'system');
        return;
    }
    const discount = data.extra?.discount || 1.0;
    let html = '';
    if (discount < 1.0) {
        html += '<p style="color:var(--accent-green);font-size:12px;margin-bottom:8px;">🔧 技术专家折扣：所有武器8折！</p>';
    }
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">';
    weapons.forEach(w => {
        const price = Math.floor(w.price * discount);
        const canBuy = data.state.funds >= price && data.state.reputation >= w.rep_required;
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;background:#222;">`;
        html += `<div style="font-weight:bold;">${w.name}</div>`;
        html += `<div style="font-size:12px;color:#888;">${w.type} · ${w.rarity}</div>`;
        html += `<div style="color:#d4a017;">战力+${w.bonus} · ¥${price}</div>`;
        html += `<div style="font-size:11px;color:#666;">需声望: ${w.rep_required}</div>`;
        if (canBuy) {
            html += `<button class="btn btn-sm" onclick="doBuyWeapon(${w.id})" style="margin-top:6px;width:100%;">购买</button>`;
        } else {
            html += `<button class="btn btn-sm" disabled style="margin-top:6px;width:100%;">${data.state.funds < price ? '资金不足' : '声望不够'}</button>`;
        }
        html += '</div>';
    });
    html += '</div>';
    showModal('🔫 武器库', html);
}

async function doBuyWeapon(weaponId) {
    closeModal();
    const data = await apiCall('buy_weapon', { weapon_id: weaponId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 训练 ---
async function handleTraining() {
    modalState = 'training';
    const data = await apiCall('training');
    if (!data) return;
    closeModal();
    const options = data.extra?.training || [];
    const idleHitmen = (data.state.hitmen || []).filter(h => h.status === 'idle');
    if (options.length === 0 || idleHitmen.length === 0) {
        appendNarrative(data.narrative, 'system');
        return;
    }
    let html = '<p>选择训练项目和杀手：</p>';
    options.forEach(t => {
        const canAfford = data.state.funds >= t.cost && data.state.ap >= t.ap;
        const bonusTag = t.has_bonus ? ' <span style="color:var(--accent-green);font-size:10px;">🏋️ +训练场加成</span>' : '';
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">`;
        html += `<div style="font-weight:bold;">${t.name}${bonusTag}</div>`;
        html += `<div style="font-size:12px;color:#888;">${t.desc}</div>`;
        html += `<div style="color:#d4a017;">¥${t.cost} · ⚡${t.ap} AP</div>`;
        if (t.min_lv) html += `<div style="font-size:11px;color:#666;">需要Lv.${t.min_lv}</div>`;
        if (!canAfford) {
            html += `<button class="btn btn-sm" disabled style="width:100%;margin-top:4px;">${data.state.funds < t.cost ? '资金不足' : 'AP不够'}</button>`;
        } else {
            idleHitmen.forEach(h => {
                const canTrain = h.lv >= (t.min_lv || 1);
                html += `<button class="btn btn-sm" onclick="doTraining('${t.id}',${h.id})" style="margin:2px;" ${!canTrain ? 'disabled' : ''}>${h.name}${!canTrain ? '(等级不够)' : ''}</button>`;
            });
        }
        html += '</div>';
    });
    showModal('💪 训练营', html);
}

async function doTraining(trainingId, hitmanId) {
    closeModal();
    const data = await apiCall('do_training', { training_id: trainingId, hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 发展（安全屋/洗钱/投资/干部） ---
async function handleDevelop() {
    const orgLevel = STATE.org_level;
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">🏗️ 组织发展选项：</p>';

    // 安全屋 (Lv2+)
    if (orgLevel >= 2) {
        html += `<div class="candidate-card" onclick="handleSafehouse()" style="cursor:pointer;">
            <div><strong>🏠 安全屋升级</strong></div>
            <div style="font-size:12px;color:var(--text-muted);">训练场、医疗室、情报室、审讯室</div>
        </div>`;
    }

    // 洗钱 (Lv4+)
    if (orgLevel >= 4) {
        const dirty = STATE.dirty_money || 0;
        html += `<div class="candidate-card" onclick="handleLaundry()" style="cursor:pointer;">
            <div><strong>🧺 洗钱 <span style="color:var(--accent-gold);">脏钱: ¥${dirty.toLocaleString()}</span></strong></div>
            <div style="font-size:12px;color:var(--text-muted);">把脏钱洗白，安全使用</div>
        </div>`;
    }

    // 干部 (Lv5+)
    if (orgLevel >= 5) {
        html += `<div class="candidate-card" onclick="handleCadres()" style="cursor:pointer;">
            <div><strong>👔 干部任命</strong></div>
            <div style="font-size:12px;color:var(--text-muted);">情报官、行动队长、技术专家、后勤主管</div>
        </div>`;
    }

    // 投资 (Lv6+)
    if (orgLevel >= 6) {
        html += `<div class="candidate-card" onclick="handleInvestments()" style="cursor:pointer;">
            <div><strong>💹 投资管理</strong></div>
            <div style="font-size:12px;color:var(--text-muted);">夜总会、赌场、房产——钱生钱</div>
        </div>`;
    }

    if (orgLevel < 2) {
        html += '<p style="color:var(--text-muted);">需要 Lv.2 区域新秀 才能解锁发展选项。</p>';
    }

    showModal('🏗️ 发展', html);
}

// --- 安全屋 ---
async function handleSafehouse() {
    const data = await apiCall('safehouse');
    if (!data) return;
    closeModal();

    if (data.error) {
        appendNarrative(data.error, 'system');
        return;
    }

    const upgrades = data.extra?.upgrades || [];
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择要升级的设施：</p>';
    if (upgrades.length === 0) {
        html += '<p style="color:var(--text-muted);">所有设施已满级。</p>';
    }

    upgrades.forEach(u => {
        const canAfford = STATE.funds >= u.cost && STATE.ap > 0;
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">
            <div style="font-weight:bold;">${u.name}</div>
            <div style="font-size:12px;color:#888;">${u.desc}</div>
            <div style="font-size:12px;color:var(--text-muted);">Lv.${u.current_lv} → Lv.${u.next_lv} / Lv.${u.max_lv}</div>
            <div style="color:#d4a017;">升级费用：¥${u.cost.toLocaleString()}</div>
            ${canAfford
                ? `<button class="btn btn-sm" onclick="doSafehouseUpgrade('${u.id}')" style="margin-top:4px;width:100%;">⬆ 升级</button>`
                : `<button class="btn btn-sm" disabled style="margin-top:4px;width:100%;">${STATE.funds < u.cost ? '资金不足' : 'AP不够'}</button>`
            }
        </div>`;
    });

    showModal('🏠 安全屋升级', html);
}

async function doSafehouseUpgrade(upgradeId) {
    closeModal();
    const data = await apiCall('upgrade_safehouse', { upgrade_id: upgradeId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 阵营声望 ---
async function handleFactions() {
    const data = await apiCall('factions');
    if (!data) return;

    if (data.error) {
        showToast(data.error);
        return;
    }

    const factions = data.extra?.factions || {};
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">城市各方势力对你的态度：</p>';

    const factionInfo = {
        police: { icon: '🚔', name: '警方', color: '#2980b9', desc: '高→不查你，低→经常突袭' },
        gang: { icon: '🔫', name: '黑帮', color: '#e74c3c', desc: '高→更多合约，低→被攻击' },
        politician: { icon: '🎩', name: '政客', color: '#d4a017', desc: '高→政治庇护，低→被施压' },
    };

    Object.entries(factions).forEach(([key, val]) => {
        const info = factionInfo[key] || { icon: '❓', name: key, color: '#888', desc: '' };
        const pct = (val.value / val.max) * 100;
        const barColor = pct > 60 ? '#27ae60' : pct > 30 ? '#d4a017' : '#c0392b';
        html += `
            <div style="border:1px solid ${info.color};border-radius:8px;padding:12px;margin-bottom:10px;background:rgba(0,0,0,0.3);">
                <div style="font-weight:bold;color:${info.color};">${info.icon} ${info.name}：${val.value}/${val.max}</div>
                <div style="margin-top:4px;height:8px;background:#2a2a3a;border-radius:4px;overflow:hidden;">
                    <div style="height:100%;width:${pct}%;background:${barColor};border-radius:4px;transition:width 0.5s;"></div>
                </div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${info.desc}</div>
            </div>
        `;
    });

    showModal('🏛️ 阵营声望', html);
}

// --- 洗钱 ---
async function handleLaundry() {
    const data = await apiCall('laundry');
    if (!data) return;
    closeModal();

    if (data.error) {
        appendNarrative(data.error, 'system');
        return;
    }

    const options = data.extra?.laundry_options || [];
    const dirty = STATE.dirty_money || 0;
    if (options.length === 0) {
        showModal('🧺 洗钱', '<p style="color:var(--text-muted);">没有脏钱需要处理，或者你还没有解锁洗钱渠道。</p>');
        return;
    }

    let html = `<p style="margin-bottom:8px;color:var(--text-secondary);">当前脏钱：<span style="color:var(--accent-gold);">¥${dirty.toLocaleString()}</span></p>`;
    options.forEach(o => {
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">
            <div style="font-weight:bold;">${o.name}</div>
            <div style="font-size:12px;color:#888;">${o.desc}</div>
            <div style="font-size:12px;color:var(--accent-gold);">预计洗白：¥${o.clean_amount.toLocaleString()}</div>
            ${o.can_use
                ? `<button class="btn btn-sm" onclick="doLaundry('${o.id}')" style="margin-top:4px;width:100%;">🧺 洗钱</button>`
                : `<button class="btn btn-sm" disabled style="margin-top:4px;width:100%;">条件不足</button>`
            }
        </div>`;
    });

    showModal('🧺 洗钱', html);
}

async function doLaundry(channelId) {
    closeModal();
    const data = await apiCall('do_laundry', { channel_id: channelId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 投资 ---
async function handleInvestments() {
    const data = await apiCall('investments');
    if (!data) return;
    closeModal();

    if (data.error) {
        appendNarrative(data.error, 'system');
        return;
    }

    const types = data.extra?.invest_types || [];
    const existing = data.extra?.existing || [];

    let html = '';
    if (existing.length > 0) {
        html += '<p style="margin-bottom:8px;color:var(--text-secondary);">现有投资：</p>';
        existing.forEach(inv => {
            html += `<div style="border:1px solid var(--accent-green);border-radius:8px;padding:8px;margin-bottom:6px;background:rgba(39,174,96,0.1);">
                <div><strong>${inv.name}</strong></div>
                <div style="font-size:12px;color:#888;">投入：¥${inv.amount.toLocaleString()} · 运营${inv.weeks_active}周 · 回报率${(inv.week_return*100).toFixed(0)}%/周</div>
            </div>`;
        });
        html += '<hr style="border-color:var(--border);margin:12px 0;">';
    }

    html += '<p style="margin-bottom:8px;color:var(--text-secondary);">选择新的投资项目：</p>';
    types.forEach(t => {
        const canAfford = STATE.funds >= t.min_invest && STATE.ap > 0;
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">
            <div style="font-weight:bold;">${t.name}</div>
            <div style="font-size:12px;color:#888;">${t.desc}</div>
            <div style="font-size:12px;color:var(--accent-gold);">最少投资：¥${t.min_invest.toLocaleString()}</div>
            ${canAfford
                ? `<button class="btn btn-sm" onclick="doMakeInvestment('${t.id}')" style="margin-top:4px;width:100%;">💹 投资</button>`
                : `<button class="btn btn-sm" disabled style="margin-top:4px;width:100%;">${STATE.funds < t.min_invest ? '资金不足' : 'AP不够'}</button>`
            }
        </div>`;
    });

    showModal('💹 投资', html);
}

async function doMakeInvestment(investId) {
    closeModal();
    const data = await apiCall('make_investment', { invest_id: investId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 干部 ---
async function handleCadres() {
    const data = await apiCall('cadres');
    if (!data) return;
    closeModal();

    if (data.error) {
        appendNarrative(data.error, 'system');
        return;
    }

    const cadres = data.extra?.cadres || {};
    const hitmen = STATE.hitmen || [];

    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">组织干部架构：</p>';

    Object.entries(cadres).forEach(([roleId, info]) => {
        const role = info.role;
        const current = info.current;
        const assigned = info.assigned;

        html += `<div style="border:1px solid var(--accent-purple);border-radius:8px;padding:12px;margin-bottom:8px;background:rgba(142,68,173,0.05);">
            <div style="font-weight:bold;color:var(--accent-purple);">${role.name}</div>
            <div style="font-size:12px;color:#888;">${role.desc}</div>
            <div style="margin-top:4px;font-size:13px;">
                当前：${current ? `<span style="color:var(--accent-green);">${current.name}</span>` : '<span style="color:var(--text-muted);">空缺</span>'}
            </div>
            ${assigned
                ? `<button class="btn btn-sm" onclick="doRemoveCadre('${roleId}')" style="margin-top:4px;font-size:11px;">解除职务</button>`
                : `<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">
                    ${hitmen.filter(h => h.status === 'idle').map(h =>
                        `<button class="btn btn-sm" onclick="doAppointCadre('${roleId}', ${h.id})" style="font-size:10px;">${h.name}</button>`
                    ).join('')}
                    ${hitmen.filter(h => h.status === 'idle').length === 0 ? '<span style="color:var(--text-muted);font-size:12px;">没有空闲杀手</span>' : ''}
                </div>`
            }
        </div>`;
    });

    showModal('👔 干部任命', html);
}

async function doAppointCadre(roleId, hitmanId) {
    closeModal();
    const data = await apiCall('appoint_cadre', { role_id: roleId, hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

async function doRemoveCadre(roleId) {
    closeModal();
    const data = await apiCall('remove_cadre', { role_id: roleId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// ============================================================
// 资源变化动画
// ============================================================

function showChange(element, amount) {
    if (!amount || amount === 0) return;
    const el = document.createElement('span');
    el.className = `resource-change ${amount > 0 ? 'positive' : 'negative'}`;
    el.textContent = `${amount > 0 ? '+' : ''}${amount}`;
    el.style.position = 'absolute';
    el.style.top = '-5px';
    el.style.right = '0';
    element.style.position = 'relative';
    element.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => el.remove(), 1300);
}

// ============================================================
// 排行榜
// ============================================================

async function handleLeaderboard() {
    const data = await apiCall('leaderboard');
    if (!data) return;
    const ranking = data.extra?.ranking || [];
    if (!ranking.length) {
        showModal('\uD83C\uDFC6 \u6392\u884C\u699C', '<p style="color:#888;">\u6682\u65E0\u6740\u624B\u6570\u636E</p>');
        return;
    }
    const apOk = data.state.ap > 0;
    const funds = data.state.funds;
    let html = '<div style="max-height:420px;overflow-y:auto;">';
    html += '<div style="display:grid;grid-template-columns:32px 1fr 32px 38px 38px;gap:2px;font-size:10px;color:#888;padding:4px 0;border-bottom:1px solid #333;">';
    html += '<span>#</span><span>\u6740\u624B</span><span style="text-align:right">\u6218</span><span style="text-align:right">\u7B49</span><span style="text-align:right">\u4EFB</span>';
    html += '</div>';
    ranking.forEach((h, i) => {
        const medal = i === 0 ? '\uD83E\uDD47' : i === 1 ? '\uD83E\uDD48' : i === 2 ? '\uD83E\uDD49' : '';
        const rankColor = i === 0 ? '#d4a017' : i === 1 ? '#94a3b8' : i === 2 ? '#cd7f32' : '#888';
        const specEmoji = { '\u6F5C\u5165':'\uD83D\uDD75\uFE0F', '\u72D9\u51FB':'\uD83C\uDFAF', '\u8FD1\u6218':'\u2694\uFE0F', '\u7206\u7834':'\uD83D\uDCA5', '\u9ED1\u5BA2':'\uD83D\uDCBB' };
        const isNpc = h.is_npc;
        const tag = isNpc ? '<span style="color:#888;font-size:9px;">\uD83D\uDC76 NPC</span>' : '<span style="color:#34d399;font-size:9px;">\uD83D\uDC9A \u6211\u7684</span>';
        const poachBtn = isNpc && !h.poached
            ? '<br><button class="btn btn-sm" onclick="doPoachLeaderboard(' + h.id + ')" style="font-size:9px;margin-top:2px;padding:2px 6px;' + (apOk && funds >= 8000 + h.skill * 5000 ? '' : 'opacity:0.4;') + '">\uD83D\uDCE5 \u6316\u89D2</button>'
            : '';
        html += '<div style="display:grid;grid-template-columns:32px 1fr 32px 38px 38px;gap:2px;align-items:center;padding:6px 0;border-bottom:1px solid #1a1a1a;">';
        html += '<span style="font-weight:700;color:' + rankColor + ';font-size:13px;">' + (medal || (i + 1)) + '</span>';
        html += '<span>' + (specEmoji[h.specialty] || '\uD83D\uDDE1\uFE0F') + ' ' + h.name + '<br>' + tag + '<span style="font-size:9px;color:#666;">' + h.specialty + '</span>' + poachBtn + '</span>';
        html += '<span style="text-align:right;color:#60a5fa;font-size:12px;">' + h.power + '</span>';
        html += '<span style="text-align:right;color:#a78bfa;font-size:11px;">Lv.' + h.lv + '</span>';
        html += '<span style="text-align:right;color:#fbbf24;font-size:11px;">' + h.missions + '</span>';
        html += '</div>';
    });
    html += '<div style="margin-top:8px;font-size:9px;color:#555;">\u8BC4\u5206 = \u6218\u529B + \u6B66\u5668\u52A0\u6210 + \u7B49\u7EA7\u00D70.5 \u00B7 \u6316\u89D2\u9700\u8981AP\u548C\u8D44\u91D1</div>';
    html += '</div>';
    showModal('\uD83C\uDFC6 \u6740\u624B\u6392\u884C\u699C', html);
}

async function doPoachLeaderboard(npcId) {
    const data = await apiCall('poach_leaderboard', { npc_id: npcId });
    if (!data) return;
    closeModal();
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// ============================================================
// Hitman 详细信息弹窗（含档案）
// ============================================================

function showHitmanDetail(hitman, cardEl) {
    const rect = cardEl.getBoundingClientRect();
    const detail = dom.hitmanDetail;
    const orgLevel = STATE.org_level;

    let fireBtnHtml = '';
    if (hitman.status === 'idle') {
        fireBtnHtml = `<button class="btn btn-danger btn-sm" onclick="handleFireHitman(${hitman.id})">🔥 解雇</button>`;
    }

    const lv = hitman.lv || 1;
    const exp = hitman.exp || 0;
    const needExp = lv * 50;
    const weapon = hitman.weapon_id ? state.weapons?.find(w => w.id === hitman.weapon_id) : null;
    const ownedWeapons = (state.weapons || []).filter(w => w.owned && !w.equipped_by);

    // 传奇称号（Lv8解锁）
    const legendTitle = hitman.legend_title || '';

    let html = `
        <div class="hd-name">${hitman.name} <span style="font-size:12px;color:#888;">Lv.${lv}</span></div>
        ${legendTitle ? `<div style="color:var(--accent-gold);font-size:12px;margin-bottom:4px;">🏆 ${legendTitle}</div>` : ''}
        <div class="hd-row"><span>专长</span><span class="hd-val">${hitman.specialty}</span></div>
        <div class="hd-row"><span>战力</span><span class="hd-val">⚔️ ${hitman.skill}/10</span></div>
        <div class="hd-row"><span>忠诚</span><span class="hd-val">❤️ ${hitman.loyalty}/10</span></div>
        <div class="hd-row"><span>状态</span><span class="hd-val">${statusText(hitman.status)}</span></div>
        <div class="hd-row"><span>抽成</span><span class="hd-val">📊 ${Math.round((hitman.cut||0.2)*100)}%</span></div>
        <div class="hd-row"><span>经验</span><span class="hd-val">${exp}/${needExp}</span></div>
        <div class="hd-row"><span>任务完成</span><span class="hd-val">${hitman.missions_completed || 0} 次</span></div>
        <div class="hd-row"><span>武器</span><span class="hd-val">${weapon ? '🔫 ' + weapon.name + '(' + weapon.rarity + ' +' + weapon.bonus + ')' : '无'}</span></div>`;

    // 个人档案按钮（Lv8解锁）
    if (orgLevel >= 8) {
        html += `<div style="margin-top:6px;"><button class="btn btn-sm btn-gold" onclick="doHitmanProfile(${hitman.id})" style="width:100%;">📋 个人档案</button></div>`;
    }

    html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
        ${fireBtnHtml}
        <button class="btn btn-sm" onclick="doInvestigate(${hitman.id})" style="margin-top:4px;width:100%;">🔍 调查内奸</button>
        ${weapon ? `<button class="btn btn-sm" onclick="doUnequipWeapon(${hitman.id})" style="margin-top:4px;width:100%;">🔧 卸下武器</button>` : ''}
        ${ownedWeapons.length > 0 && hitman.status === 'idle' ? ownedWeapons.map(w => `<button class="btn btn-sm" onclick="doEquipWeapon(${hitman.id},${w.id})" style="margin:2px;">🔫 ${w.name}(${w.rarity})</button>`).join('') : ''}
    </div>`;

    detail.innerHTML = html;

    detail.classList.remove('hidden');
    detail.style.left = Math.min(rect.left - 220, window.innerWidth - 240) + 'px';
    detail.style.top = Math.min(rect.top, window.innerHeight - 400) + 'px';
}

async function doInvestigate(hitmanId) {
    const data = await apiCall('investigate', { hitman_id: hitmanId });
    if (!data) return;
    appendNarrative(data.narrative, 'system');
}

// --- 杀手个人档案（Lv8） ---
async function doHitmanProfile(hitmanId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('hitman_profile', { hitman_id: hitmanId });
    if (!data) return;

    const p = data.extra?.profile;
    if (!p) return;

    let html = `
        <div style="margin-bottom:12px;">
            <div style="font-size:20px;font-weight:700;">${p.name}</div>
            <div style="font-size:14px;color:var(--accent-gold);">🏆 ${p.legend_title || '新手'}</div>
            <div style="font-size:12px;color:var(--text-muted);">${p.specialty} · Lv.${p.lv} · 战力${p.skill}</div>
        </div>
        <div style="margin-bottom:12px;">
            <div style="border:1px solid var(--border);border-radius:8px;padding:10px;background:var(--bg-card);">
                <div style="font-size:12px;color:var(--text-muted);">基础信息</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:6px;font-size:13px;">
                    <span>忠诚：❤️ ${p.loyalty}/10</span>
                    <span>任务：📊 ${p.missions_completed}次</span>
                    <span>状态：${statusText(p.status)}</span>
                    <span>朋友：${p.friends?.length || 0}人</span>
                    <span>对手：${p.rivals?.length || 0}人</span>
                </div>
            </div>
        </div>
        <div>
            <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">任务履历：</div>
            ${(p.mission_history || []).length === 0
                ? '<div style="color:var(--text-muted);font-size:12px;">还没有执行过任务。</div>'
                : (p.mission_history || []).slice(-10).reverse().map(m =>
                    `<div style="border:1px solid var(--border);border-radius:6px;padding:6px 10px;margin-bottom:4px;font-size:12px;display:flex;justify-content:space-between;background:var(--bg-card);">
                        <span>${m.contract} (${m.difficulty})</span>
                        <span style="color:${m.result === 'success' ? 'var(--accent-green)' : 'var(--accent-red)'};">${m.result === 'success' ? '✅' : '❌'} ¥${m.reward.toLocaleString()}</span>
                    </div>`
                ).join('')
            }
        </div>
        ${p.epitaph ? `<div style="margin-top:12px;padding:10px;border:1px solid #444;border-radius:8px;background:#1a1a1a;font-style:italic;color:#888;text-align:center;">${p.epitaph}</div>` : ''}
    `;

    showModal(`📋 ${p.name} 的档案`, html);
}

// 点击其他地方关闭详情
document.addEventListener('click', (e) => {
    if (!dom.hitmanDetail.contains(e.target) && !e.target.closest('.hitman-card')) {
        dom.hitmanDetail.classList.add('hidden');
    }
});

// ============================================================
// 工具函数
// ============================================================

function formatMoney(amount) {
    if (amount === undefined || amount === null) return '¥0';
    return '¥' + Number(amount).toLocaleString('zh-CN');
}

function setLoading(isLoading) {
    loading = isLoading;
    dom.loadingOverlay.classList.toggle('hidden', !isLoading);
    dom.loadingText.textContent = isLoading ? '枭正在收集情报……' : '';
}

function disableGameButtons() {
    const buttons = dom.actionBar?.querySelectorAll('button') || [];
    document.querySelectorAll('.action-bar .btn').forEach(b => b.disabled = true);
    dom.btnEndDay.disabled = true;
    if (dom.btnRestart) dom.btnRestart.classList.remove('hidden');
}

function apiCallAndRefresh(action, params) {
    return new Promise(async (resolve) => {
        const data = await apiCall(action, params);
        if (!data) { resolve(null); return; }
        updateStats(data.state);
        if (data.narrative) appendNarrative(data.narrative, 'narrative');
        setLoading(false);
        resolve(data);
    });
}

// ============================================================
// 事件绑定
// ============================================================

dom.btnStart.addEventListener('click', handleStart);
dom.btnContracts.addEventListener('click', handleShowContracts);
dom.btnRecruit.addEventListener('click', handleRecruit);
dom.btnDevelop.addEventListener('click', handleDevelop);
dom.btnFactions.addEventListener('click', handleFactions);
dom.btnEndDay.addEventListener('click', handleEndDay);
dom.btnSave.addEventListener('click', handleSave);
dom.btnLoad.addEventListener('click', handleLoad);
dom.btnRestart.addEventListener('click', handleRestart);
dom.btnRivals.addEventListener('click', handleRivals);
dom.btnWeaponShop.addEventListener('click', handleWeaponShop);
dom.btnTraining.addEventListener('click', handleTraining);
dom.btnLeaderboard.addEventListener('click', handleLeaderboard);
dom.resetLink.addEventListener('click', async function() {
    if (!confirm('确定要重置游戏吗？所有进度将丢失。')) return;
    const data = await apiCall('reset');
    if (!data) return;
    gameStarted = false;
    clearNarrative();
    updateStats(data.state);
    dom.startScreen.classList.remove('hidden');
    dom.gameUI.classList.add('hidden');
    setLoading(false);
});

// ============================================================
// 键盘快捷键
// ============================================================

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (!dom.modalOverlay.classList.contains('hidden')) {
            closeModal();
        }
    }
});

// ============================================================
// 初始化
// ============================================================

// 挂载 closeModal 到全局供内联 onclick 调用
window.closeModal = closeModal;

console.log('🗡️ 杀手组织老板模拟器 v2 loaded');
console.log('💡 纯按钮操作，开启你的暗面帝国吧');
