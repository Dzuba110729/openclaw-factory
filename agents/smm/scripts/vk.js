#!/usr/bin/env node
/**
 * VK API helper for SMM agent
 * Usage:
 *   node vk.js post --text "текст" [--image /path/to/img.jpg]
 *   node vk.js stat
 *   node vk.js comments [--post_id 123]
 *   node vk.js pending            — только неотвеченные, JSON; exit 10 = тишина
 *   node vk.js reply --comment_id 123 --post_id 456 --text "ответ"
 *   node vk.js schedule --text "текст" --date "2026-03-23 12:00" [--image /path/to/img.jpg]
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Загружаем переменные из .env
const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const [k, v] = line.split('=');
    if (k && v) process.env[k.trim()] = v.trim();
  });
}

const TOKEN = process.env.VK_TOKEN;
const USER_TOKEN = process.env.VK_USER_TOKEN;
const GROUP_ID = process.env.VK_GROUP_ID;
if (!GROUP_ID) { console.error('VK_GROUP_ID не задан: добавь его в agents/smm/.env'); process.exit(2); }
const V = '5.199';

// Журнал уже отвеченных комментариев
const REPLIED_FILE = path.join(__dirname, '..', 'memory', 'replied-comments.json');
function loadReplied() {
  if (fs.existsSync(REPLIED_FILE)) {
    try { return new Set(JSON.parse(fs.readFileSync(REPLIED_FILE, 'utf8'))); } catch {}
  }
  return new Set();
}
function saveReplied(set) {
  fs.mkdirSync(path.dirname(REPLIED_FILE), { recursive: true });
  fs.writeFileSync(REPLIED_FILE, JSON.stringify([...set], null, 2));
}
function markReplied(commentId) {
  const set = loadReplied();
  set.add(String(commentId));
  saveReplied(set);
}
function isReplied(commentId) {
  return loadReplied().has(String(commentId));
}

// --- Long Poll сообщества ---------------------------------------------------
// Новые комментарии приходят событиями wall_reply_new на ГРУППОВОМ токене.
// Пользовательский токен здесь не нужен: wall.getComments нам ВК не даёт
// (ошибка 1051), а события — отдаёт.

const LP_STATE_FILE = path.join(__dirname, '..', 'memory', 'vk-longpoll.json');
const QUEUE_FILE = path.join(__dirname, '..', 'memory', 'vk-pending.json');

function loadJson(file, fallback) {
  if (fs.existsSync(file)) {
    try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch {}
  }
  return fallback;
}
function saveJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

// Очередь неотвеченных живёт на диске: события Long Poll отдаются один раз,
// а агент может разобрать их не сразу.
function loadQueue() { return loadJson(QUEUE_FILE, []); }
function saveQueue(q) { saveJson(QUEUE_FILE, q); }

function dropFromQueue(commentId) {
  const q = loadQueue().filter(c => String(c.comment_id) !== String(commentId));
  saveQueue(q);
}

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      let body = '';
      res.on('data', d => (body += d));
      res.on('end', () => {
        try { resolve(JSON.parse(body)); } catch (e) { reject(e); }
      });
    }).setTimeout(30000, function () { this.destroy(new Error('VK request timeout 30s')); }).on('error', reject);
  });
}

// Забирает новые события и складывает комментарии в очередь.
async function pollLongPoll() {
  const srv = await apiCall('groups.getLongPollServer', { group_id: GROUP_ID });
  if (!srv || !srv.server) throw new Error('Long Poll не выдан. Включи его: groups.setLongPollSettings');

  const state = loadJson(LP_STATE_FILE, {});
  let ts = state.ts || srv.ts;

  let data = await httpGetJson(`${srv.server}?act=a_check&key=${srv.key}&ts=${ts}&wait=1`);

  // ts устарел или ключ протух — начинаем с текущей точки
  if (data.failed) {
    if (data.ts) ts = data.ts;
    else ts = srv.ts;
    data = await httpGetJson(`${srv.server}?act=a_check&key=${srv.key}&ts=${ts}&wait=1`);
  }

  saveJson(LP_STATE_FILE, { ts: data.ts || ts, updated: new Date().toISOString() });

  const queue = loadQueue();
  const known = new Set(queue.map(c => String(c.comment_id)));
  let added = 0;

  for (const u of data.updates || []) {
    if (u.type !== 'wall_reply_new') continue;
    const o = u.object || {};
    if (String(o.from_id) === `-${GROUP_ID}`) continue;   // свои же ответы
    if (isReplied(o.id) || known.has(String(o.id))) continue;
    queue.push({
      comment_id: o.id,
      post_id: o.post_id,
      from_id: o.from_id,
      text: o.text || '',
      date: new Date((o.date || 0) * 1000).toISOString(),
    });
    known.add(String(o.id));
    added++;
  }

  if (added) saveQueue(queue);
  return queue.filter(c => !isReplied(c.comment_id));
}

if (!TOKEN) {
  console.error('❌ VK_TOKEN не найден в .env');
  process.exit(1);
}

function apiCall(method, params = {}, token = TOKEN) {
  return new Promise((resolve, reject) => {
    const query = new URLSearchParams({ ...params, access_token: token, v: V }).toString();
    const url = `https://api.vk.com/method/${method}?${query}`;
    https.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.error) reject(new Error(`VK API error: ${json.error.error_msg}`));
          else resolve(json.response);
        } catch (e) { reject(e); }
      });
    }).setTimeout(30000, function () { this.destroy(new Error('VK request timeout 30s')); }).on('error', reject);
  });
}

function apiPost(method, params = {}, token = TOKEN) {
  return new Promise((resolve, reject) => {
    const postData = new URLSearchParams({ ...params, access_token: token, v: V }).toString();
    const options = {
      hostname: 'api.vk.com',
      path: `/method/${method}`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(postData),
      }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.error) reject(new Error(`VK API error: ${json.error.error_msg}`));
          else resolve(json.response);
        } catch (e) { reject(e); }
      });
    });
    req.setTimeout(30000, () => req.destroy(new Error('VK request timeout 30s')));
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function uploadPhoto(imagePath) {
  // 1. Получаем URL для загрузки (нужен user token)
  const uploadToken = USER_TOKEN || TOKEN;
  const uploadServer = await apiCall('photos.getWallUploadServer', { group_id: GROUP_ID }, uploadToken);
  const uploadUrl = uploadServer.upload_url;

  // 2. Загружаем файл через multipart form
  const boundary = '----FormBoundary' + Math.random().toString(36).slice(2);
  const fileContent = fs.readFileSync(imagePath);
  const fileName = path.basename(imagePath);

  const body = Buffer.concat([
    Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="photo"; filename="${fileName}"\r\nContent-Type: image/png\r\n\r\n`),
    fileContent,
    Buffer.from(`\r\n--${boundary}--\r\n`)
  ]);

  const uploadResult = await new Promise((resolve, reject) => {
    const urlObj = new URL(uploadUrl);
    const options = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': body.length,
      }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data)));
    });
    req.setTimeout(30000, () => req.destroy(new Error('VK request timeout 30s')));
    req.on('error', reject);
    req.write(body);
    req.end();
  });

  // 3. Сохраняем фото
  const saved = await apiPost('photos.saveWallPhoto', {
    group_id: GROUP_ID,
    photo: uploadResult.photo,
    server: uploadResult.server,
    hash: uploadResult.hash,
  }, uploadToken);

  return `photo${saved[0].owner_id}_${saved[0].id}`;
}

async function cmdPost(args) {
  const textIdx = args.indexOf('--text');
  const imgIdx = args.indexOf('--image');
  const text = textIdx >= 0 ? args[textIdx + 1] : '';
  const imagePath = imgIdx >= 0 ? args[imgIdx + 1] : null;

  const params = {
    owner_id: `-${GROUP_ID}`,
    from_group: 1,
    message: text,
  };

  if (imagePath) {
    console.log('📤 Загружаю изображение...');
    const attachment = await uploadPhoto(imagePath);
    params.attachments = attachment;
    console.log(`✅ Изображение загружено: ${attachment}`);
  }

  // Публикуем от имени группы через user token (требует прав manage в группе)
  const postToken = USER_TOKEN || TOKEN;
  const result = await apiPost('wall.post', params, postToken);
  console.log(`✅ Пост опубликован! ID: ${result.post_id}`);
  console.log(`🔗 https://vk.com/wall-${GROUP_ID}_${result.post_id}`);
  return result;
}

async function cmdSchedule(args) {
  const textIdx = args.indexOf('--text');
  const dateIdx = args.indexOf('--date');
  const imgIdx = args.indexOf('--image');
  const text = textIdx >= 0 ? args[textIdx + 1] : '';
  const dateStr = dateIdx >= 0 ? args[dateIdx + 1] : null;
  const imagePath = imgIdx >= 0 ? args[imgIdx + 1] : null;

  if (!dateStr) { console.error('❌ Нужен --date "YYYY-MM-DD HH:MM"'); process.exit(1); }

  const publishDate = Math.floor(new Date(dateStr).getTime() / 1000);
  const params = {
    owner_id: `-${GROUP_ID}`,
    from_group: 1,
    message: text,
    publish_date: publishDate,
  };

  if (imagePath) {
    console.log('📤 Загружаю изображение...');
    const attachment = await uploadPhoto(imagePath);
    params.attachments = attachment;
  }

  const postToken = USER_TOKEN || TOKEN;
  const result = await apiPost('wall.post', params, postToken);
  console.log(`✅ Пост запланирован на ${dateStr}! ID: ${result.post_id}`);
  console.log(`🔗 https://vk.com/wall-${GROUP_ID}_${result.post_id}`);
  return result;
}

async function cmdStat() {
  // stats.get групповому токену недоступен (ошибка 27), а пользовательские токены
  // ВК для этой установки блокирует. Показываем то, что реально доступно.
  if (!USER_TOKEN) {
    const info = await apiCall('groups.getById', { group_id: GROUP_ID, fields: 'members_count,activity' });
    const g = (info.groups || info)[0] || {};
    console.log('📊 Группа: ' + (g.name || GROUP_ID));
    console.log(`👥 Подписчиков: ${g.members_count ?? '—'}`);
    console.log('');
    console.log('ℹ️  Полная статистика (просмотры, охват, активность) требует');
    console.log('   пользовательского токена: stats.get закрыт для групповых.');
    console.log('   Смотри в ВК: Управление → Статистика.');
    return;
  }
  const stat = await apiCall('stats.get', {
    group_id: GROUP_ID,
    timestamp_from: Math.floor(Date.now() / 1000) - 7 * 24 * 3600,
    timestamp_to: Math.floor(Date.now() / 1000),
    stats_groups: 'visitors,activity',
    extended: 1,
  }, USER_TOKEN);
  console.log('📊 Статистика за 7 дней:');
  if (Array.isArray(stat)) {
    let totalViews = 0, totalVisitors = 0, totalLikes = 0, totalComments = 0, totalReposts = 0;
    stat.forEach(d => {
      if (d.visitors) { totalViews += d.visitors.views || 0; totalVisitors += d.visitors.visitors || 0; }
      if (d.activity) { totalLikes += d.activity.likes || 0; totalComments += d.activity.comments || 0; totalReposts += d.activity.reposts || 0; }
    });
    console.log(`👁 Просмотры: ${totalViews}`);
    console.log(`👤 Уникальные посетители: ${totalVisitors}`);
    console.log(`❤️  Лайки: ${totalLikes}`);
    console.log(`💬 Комментарии: ${totalComments}`);
    console.log(`🔄 Репосты: ${totalReposts}`);
  } else {
    console.log(JSON.stringify(stat, null, 2));
  }
}

async function cmdComments(args) {
  // wall.get / wall.getComments ВК закрыл: групповому токену — ошибка 27,
  // пользовательскому (VK ID) — 1051. Новые комментарии приходят событиями,
  // поэтому показываем накопленную очередь, а не опрашиваем стену.
  const queue = loadQueue().filter(c => !isReplied(c.comment_id));

  if (queue.length === 0) {
    console.log('Неотвеченных комментариев нет.');
    console.log('');
    console.log('ℹ️  Комментарии собираются событиями сообщества (Long Poll).');
    console.log('   Учитываются только появившиеся после включения — 14.09.2026.');
    console.log('   Более старые смотри в ВК вручную.');
    return;
  }

  console.log(`💬 Неотвеченных комментариев: ${queue.length}\n`);
  for (const c of queue) {
    console.log(`  [${c.comment_id}] пост ${c.post_id}, от ${c.from_id}, ${c.date}`);
    console.log(`     ${c.text}`);
    console.log(`     ответить: node vk.js reply --comment_id ${c.comment_id} --post_id ${c.post_id} --text "…"`);
    console.log('');
  }
}

// Только неотвеченные комментарии. Машиночитаемо, для крон-гейта.
// Код возврата: 0 — есть что отвечать, 10 — тишина, 1 — ошибка.
async function cmdPending(args) {
  const pending = await pollLongPoll();

  if (pending.length === 0) {
    console.log('QUIET');
    process.exitCode = 10;
    return;
  }
  console.log(JSON.stringify(pending, null, 2));
  process.exitCode = 0;
}

async function cmdReply(args) {
  const commentIdx = args.indexOf('--comment_id');
  const postIdx = args.indexOf('--post_id');
  const textIdx = args.indexOf('--text');

  const commentId = commentIdx >= 0 ? args[commentIdx + 1] : null;
  const postId = postIdx >= 0 ? args[postIdx + 1] : null;
  const text = textIdx >= 0 ? args[textIdx + 1] : '';

  if (!commentId || !postId || !text) {
    console.error('❌ Нужны: --comment_id, --post_id, --text');
    process.exit(1);
  }

  if (isReplied(commentId)) {
    console.log(`⚠️  Комментарий ${commentId} уже отмечен как отвеченный. Пропускаю.`);
    return;
  }

  const result = await apiPost('wall.createComment', {
    owner_id: `-${GROUP_ID}`,
    post_id: postId,
    reply_to_comment: commentId,
    message: text,
    from_group: GROUP_ID,
  });
  markReplied(commentId);
  dropFromQueue(commentId);
  console.log(`✅ Ответ опубликован! comment_id: ${result.comment_id}`);
}

// Роутер команд
const [,, cmd, ...args] = process.argv;
(async () => {
  try {
    switch (cmd) {
      case 'post': await cmdPost(args); break;
      case 'schedule': await cmdSchedule(args); break;
      case 'stat': await cmdStat(); break;
      case 'comments': await cmdComments(args); break;
      case 'pending': await cmdPending(args); break;
      case 'reply': await cmdReply(args); break;
      default:
        console.log('Команды: post, schedule, stat, comments, reply');
        console.log('Пример: node vk.js post --text "Привет мир"');
    }
  } catch (e) {
    console.error('❌', e.message);
    process.exit(1);
  }
})();
