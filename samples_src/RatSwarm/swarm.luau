-- Rat swarm: a self-running swarm of top-down rats that fills its layout box.
--
-- Inputs (bound to the Swarm view model):
--   hp, maxHp  fraction alive = hp / maxHp. Rats die in a fixed random order;
--              dead rats stop and leave a corpse with blood, or vanish.
--              hp <= 0 fades the whole swarm out.
--   ratScale   rat size multiplier (default 1). Spacing scales with it too.
--
-- Density is constant: one rat per SPACING^2 points of area, so a bigger
-- artboard gets proportionally more rats.

local BASE_UNIT = 11 -- rat body unit in points (body ~1.3 units long, tail ~1)
local SPACING = 22 -- average distance between rats, in points, at ratScale 1
local MAX_RATS = 1500
local CORPSE_CHANCE = 0.6 -- share of dead rats that leave a corpse (rest vanish)
local DEATH_RATE = 2.5 -- how fast death / revival transitions play (per second)
local FADE_RATE = 1.6 -- whole-swarm fade at hp 0

type Blob = { x: number, y: number, r: number, dark: boolean }

type Rat = {
    x: number,
    y: number,
    heading: number,
    speed: number,
    targetSpeed: number,
    turnRate: number,
    timer: number,
    dashing: boolean,
    phase: number,
    color: number,
    size: number,
    rank: number,
    corpse: boolean,
    dead: boolean,
    d: number, -- 0 = fully alive, 1 = fully dead (animated)
    curl: number,
    blobs: { Blob },
}

type Swarm = {
    hp: Input<number>,
    maxHp: Input<number>,
    ratScale: Input<number>,

    size: Vector,
    rats: { Rat },
    order: { Rat },
    aliveCount: number,
    fade: number,
    lastHp: number,
    lastMax: number,
    lastScale: number,
    lastW: number,
    lastH: number,
    cells: { [number]: { Rat } },

    shadowPath: Path,
    bloodDarkPath: Path,
    bloodPath: Path,
    corpseTailPath: Path,
    corpsePath: Path,
    bellyPath: Path,
    corpseEarPath: Path,
    tailPath: Path,
    bodyPaths: { Path },
    earPath: Path,
    eyePath: Path,

    shadowPaint: Paint,
    bloodDarkPaint: Paint,
    bloodPaint: Paint,
    corpseTailPaint: Paint,
    corpsePaint: Paint,
    bellyPaint: Paint,
    corpseEarPaint: Paint,
    tailPaint: Paint,
    bodyPaints: { Paint },
    earPaint: Paint,
    eyePaint: Paint,
}

-- Body outline in rat-local units, nose along +x. Wound clockwise (y down).
local BODY: { number } = {
    0.80, 0.00,
    0.56, 0.14,
    0.32, 0.19,
    0.02, 0.27,
    -0.32, 0.24,
    -0.53, 0.00,
    -0.32, -0.24,
    0.02, -0.27,
    0.32, -0.19,
    0.56, -0.14,
}
local BODY_N = #BODY // 2

local SX: { number } = table.create(16, 0)
local SY: { number } = table.create(16, 0)

local function rand(a: number, b: number): number
    return a + (b - a) * math.random()
end

local function clamp(v: number, a: number, b: number): number
    if v < a then
        return a
    elseif v > b then
        return b
    end
    return v
end

local function smooth(t: number): number
    local c = clamp(t, 0, 1)
    return c * c * (3 - 2 * c)
end

local function unitOf(self: Swarm): number
    local s = self.ratScale
    if s <= 0 then
        s = 1
    end
    return BASE_UNIT * s
end

-- Closed Catmull-Rom spline through SX/SY[1..n], as cubics.
local function addClosedSpline(path: Path, n: number)
    path:moveTo(Vector.xy(SX[1], SY[1]))
    for i = 1, n do
        local i0 = ((i - 2) % n) + 1
        local i2 = (i % n) + 1
        local i3 = ((i + 1) % n) + 1
        local c1x = SX[i] + (SX[i2] - SX[i0]) / 6
        local c1y = SY[i] + (SY[i2] - SY[i0]) / 6
        local c2x = SX[i2] - (SX[i3] - SX[i]) / 6
        local c2y = SY[i2] - (SY[i3] - SY[i]) / 6
        path:cubicTo(Vector.xy(c1x, c1y), Vector.xy(c2x, c2y), Vector.xy(SX[i2], SY[i2]))
    end
    path:close()
end

-- Circle wound clockwise (y down), matching the body.
local K = 0.5523
local function addCircle(path: Path, x: number, y: number, r: number)
    local k = r * K
    path:moveTo(Vector.xy(x + r, y))
    path:cubicTo(Vector.xy(x + r, y + k), Vector.xy(x + k, y + r), Vector.xy(x, y + r))
    path:cubicTo(Vector.xy(x - k, y + r), Vector.xy(x - r, y + k), Vector.xy(x - r, y))
    path:cubicTo(Vector.xy(x - r, y - k), Vector.xy(x - k, y - r), Vector.xy(x, y - r))
    path:cubicTo(Vector.xy(x + k, y - r), Vector.xy(x + r, y - k), Vector.xy(x + r, y))
    path:close()
end

local function addBody(path: Path, r: Rat, u: number, bend: number, widen: number, ox: number, oy: number)
    local c = math.cos(r.heading)
    local s = math.sin(r.heading)
    for i = 1, BODY_N do
        local lx = BODY[i * 2 - 1]
        local ly = BODY[i * 2] * widen + bend * lx * lx
        SX[i] = r.x + ox + (lx * c - ly * s) * u
        SY[i] = r.y + oy + (lx * s + ly * c) * u
    end
    addClosedSpline(path, BODY_N)
end

-- Local point -> world, for small features.
local function addFeature(path: Path, r: Rat, u: number, lx: number, ly: number, rad: number)
    local c = math.cos(r.heading)
    local s = math.sin(r.heading)
    addCircle(path, r.x + (lx * c - ly * s) * u, r.y + (lx * s + ly * c) * u, rad * u)
end

local function addTail(path: Path, r: Rat, u: number, wiggle: number, curl: number, bend: number)
    local c = math.cos(r.heading)
    local s = math.sin(r.heading)
    local segs = 6
    for k = 0, segs do
        local t = k / segs
        local lx = -0.48 - t * 1.05
        local ly = math.sin(r.phase * 1.3 - t * 3.2) * wiggle * t * 0.28 + curl * t * t + bend * lx * lx * 0.6
        local p = Vector.xy(r.x + (lx * c - ly * s) * u, r.y + (lx * s + ly * c) * u)
        if k == 0 then
            path:moveTo(p)
        else
            path:lineTo(p)
        end
    end
end

local function makeBlobs(): { Blob }
    local blobs: { Blob } = {}
    -- the pool under the body: a few overlapping dark circles
    local pools = math.random(2, 3)
    for _ = 1, pools do
        table.insert(blobs, { x = rand(-0.45, 0.35), y = rand(-0.3, 0.3), r = rand(0.3, 0.5), dark = true })
    end
    -- spatter around it
    local spats = math.random(5, 9)
    for _ = 1, spats do
        local a = rand(0, math.pi * 2)
        local dist = rand(0.5, 1.15)
        table.insert(blobs, { x = math.cos(a) * dist, y = math.sin(a) * dist, r = rand(0.05, 0.15), dark = false })
    end
    return blobs
end

local function newRat(w: number, h: number): Rat
    return {
        x = rand(0, w),
        y = rand(0, h),
        heading = rand(0, math.pi * 2),
        speed = 0,
        targetSpeed = 0,
        turnRate = 0,
        timer = rand(0, 1),
        dashing = math.random() < 0.5,
        phase = rand(0, 10),
        color = math.random(1, 3),
        size = rand(0.85, 1.15),
        rank = math.random(),
        corpse = math.random() < CORPSE_CHANCE,
        dead = false,
        d = 0,
        curl = rand(-0.5, 0.5),
        blobs = {},
    }
end

local function aliveFraction(self: Swarm): number
    local hp = self.hp
    local maxHp = self.maxHp
    if hp <= 0 then
        return 0
    end
    if maxHp <= 0 then
        return 1
    end
    return clamp(hp / maxHp, 0, 1)
end

-- Decide which rats are alive: the lowest ranks live.
local function applyHealth(self: Swarm)
    local n = #self.order
    local frac = aliveFraction(self)
    local alive = 0
    if frac > 0 and n > 0 then
        alive = math.max(1, math.floor(n * frac + 0.5))
    end
    self.aliveCount = alive
    for i, r in self.order do
        local shouldDie = i > alive
        if shouldDie and not r.dead then
            r.dead = true
            r.speed = 0
            if r.corpse then
                r.blobs = makeBlobs()
            end
        elseif not shouldDie and r.dead then
            r.dead = false
            r.timer = 0
        end
    end
end

-- Grow or shrink the population to match the box area.
local function populate(self: Swarm)
    local w = self.size.x
    local h = self.size.y
    local u = unitOf(self)
    local spacing = SPACING * (u / BASE_UNIT)
    local target = 0
    if w > 0 and h > 0 then
        target = clamp(math.floor(w * h / (spacing * spacing) + 0.5), 1, MAX_RATS)
    end
    local rats = self.rats
    while #rats < target do
        table.insert(rats, newRat(w, h))
    end
    while #rats > target do
        table.remove(rats)
    end
    for _, r in rats do
        r.x = clamp(r.x, 0, w)
        r.y = clamp(r.y, 0, h)
    end
    local order: { Rat } = table.clone(rats)
    table.sort(order, function(a: Rat, b: Rat): boolean
        return a.rank < b.rank
    end)
    self.order = order
    self.lastW = w
    self.lastH = h
    self.lastScale = self.ratScale
    applyHealth(self)
end

local function syncInputs(self: Swarm)
    if self.size.x ~= self.lastW or self.size.y ~= self.lastH or self.ratScale ~= self.lastScale then
        populate(self)
    end
    if self.hp ~= self.lastHp or self.maxHp ~= self.lastMax then
        self.lastHp = self.hp
        self.lastMax = self.maxHp
        applyHealth(self)
    end
end

function init(self: Swarm, context: Context): boolean
    return true
end

function resize(self: Swarm, size: Vector, scale: number)
    self.size = size
    populate(self)
end

function update(self: Swarm)
    syncInputs(self)
end

local function steer(r: Rat, dt: number, u: number, w: number, h: number)
    r.timer -= dt
    if r.timer <= 0 then
        r.dashing = not r.dashing
        if r.dashing then
            r.targetSpeed = rand(2.5, 6.0) * u
            r.timer = rand(0.35, 1.3)
            r.turnRate = rand(-2.2, 2.2)
        else
            r.targetSpeed = rand(0, 0.35) * u
            r.timer = rand(0.15, 0.8)
            r.turnRate = rand(-5, 5)
        end
    end
    r.speed += (r.targetSpeed - r.speed) * math.min(1, dt * 9)
    r.turnRate += rand(-12, 12) * dt
    r.turnRate = clamp(r.turnRate, -6, 6)
    r.heading += r.turnRate * dt

    -- keep inside the box: turn toward the interior near edges
    local m = u * 1.1
    if r.x < m or r.x > w - m or r.y < m or r.y > h - m then
        local want = math.atan2(h * 0.5 + rand(-h, h) * 0.25 - r.y, w * 0.5 + rand(-w, w) * 0.25 - r.x)
        local diff = (want - r.heading + math.pi) % (math.pi * 2) - math.pi
        r.heading += clamp(diff, -7 * dt, 7 * dt)
    end

    r.x += math.cos(r.heading) * r.speed * dt
    r.y += math.sin(r.heading) * r.speed * dt
    local edge = u * 0.55
    r.x = clamp(r.x, edge, math.max(edge, w - edge))
    r.y = clamp(r.y, edge, math.max(edge, h - edge))
    r.phase += dt * (3 + r.speed / u * 2.2)
end

-- Gentle separation so live rats crowd rather than stack.
local function separate(self: Swarm, u: number)
    local cell = u * 1.2
    local cells = self.cells
    for _, list in cells do
        table.clear(list)
    end
    local cols = 4096
    for _, r in self.rats do
        if not r.dead then
            local key = math.floor(r.x / cell) * cols + math.floor(r.y / cell)
            local list = cells[key]
            if list == nil then
                list = {}
                cells[key] = list
            end
            table.insert(list, r)
        end
    end
    local minD = u * 0.9
    local minD2 = minD * minD
    for _, r in self.rats do
        if not r.dead then
            local cx = math.floor(r.x / cell)
            local cy = math.floor(r.y / cell)
            for gx = cx - 1, cx + 1 do
                for gy = cy - 1, cy + 1 do
                    local list = cells[gx * cols + gy]
                    if list ~= nil then
                        for _, o in list do
                            if o ~= r then
                                local dx = r.x - o.x
                                local dy = r.y - o.y
                                local d2 = dx * dx + dy * dy
                                if d2 < minD2 and d2 > 0.0001 then
                                    local d = math.sqrt(d2)
                                    local push = (minD - d) * 0.25
                                    r.x += dx / d * push
                                    r.y += dy / d * push
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end

function advance(self: Swarm, seconds: number): boolean
    local dt = math.min(seconds, 0.1)
    syncInputs(self)
    local w = self.size.x
    local h = self.size.y
    local u = unitOf(self)

    local fadeTarget = if self.aliveCount > 0 then 1 else 0
    if self.fade < fadeTarget then
        self.fade = math.min(fadeTarget, self.fade + dt * FADE_RATE * 2)
    elseif self.fade > fadeTarget then
        self.fade = math.max(fadeTarget, self.fade - dt * FADE_RATE)
    end

    for _, r in self.rats do
        if r.dead then
            r.d = math.min(1, r.d + dt * DEATH_RATE)
        else
            r.d = math.max(0, r.d - dt * DEATH_RATE)
            steer(r, dt, u * r.size, w, h)
        end
    end
    separate(self, u)
    return true
end

function draw(self: Swarm, renderer: Renderer)
    if self.fade <= 0.001 then
        return
    end
    local base = unitOf(self)

    self.shadowPath:reset()
    self.bloodDarkPath:reset()
    self.bloodPath:reset()
    self.corpseTailPath:reset()
    self.corpsePath:reset()
    self.bellyPath:reset()
    self.corpseEarPath:reset()
    self.tailPath:reset()
    for _, p in self.bodyPaths do
        p:reset()
    end
    self.earPath:reset()
    self.eyePath:reset()

    for _, r in self.rats do
        local u = base * r.size
        if r.dead and r.corpse then
            -- blood grows in, corpse lies still
            local g = smooth(r.d * 1.3)
            if g > 0.01 then
                local c = math.cos(r.heading)
                local s = math.sin(r.heading)
                for _, b in r.blobs do
                    local bx = r.x + (b.x * c - b.y * s) * u
                    local by = r.y + (b.x * s + b.y * c) * u
                    local path = if b.dark then self.bloodDarkPath else self.bloodPath
                    addCircle(path, bx, by, b.r * u * g)
                end
            end
            local bend = r.curl * 0.35
            addTail(self.corpseTailPath, r, u, 0, r.curl * 0.6, bend)
            addBody(self.corpsePath, r, u, bend, 1.25, 0, 0)
            addBody(self.bellyPath, r, u * 0.62, bend, 1.2, 0, 0)
            addFeature(self.corpseEarPath, r, u, 0.40, 0.20, 0.08)
            addFeature(self.corpseEarPath, r, u, 0.40, -0.20, 0.08)
            addFeature(self.corpseEarPath, r, u, 0.22, 0.36, 0.065)
            addFeature(self.corpseEarPath, r, u, 0.22, -0.36, 0.065)
            addFeature(self.corpseEarPath, r, u, -0.25, 0.34, 0.07)
            addFeature(self.corpseEarPath, r, u, -0.25, -0.34, 0.07)
        elseif r.dead and r.d >= 1 then
            -- vanished
        elseif not r.dead and r.d > 0 and r.corpse then
            -- reviving corpse: blood fades out, rat already moving
            local g = smooth(r.d)
            local c = math.cos(r.heading)
            local s = math.sin(r.heading)
            for _, b in r.blobs do
                local bx = r.x + (b.x * c - b.y * s) * u
                local by = r.y + (b.x * s + b.y * c) * u
                local path = if b.dark then self.bloodDarkPath else self.bloodPath
                addCircle(path, bx, by, b.r * u * g)
            end
        end

        local vanishing = (not r.corpse) and r.d > 0
        local drawLive = (not r.dead) or (vanishing and r.d < 1)
        if drawLive then
            local su = u
            if vanishing then
                su = u * (1 - smooth(r.d))
            end
            if su > 0.05 then
                local running = clamp(r.speed / (u * 4), 0, 1)
                local bend = math.sin(r.phase * 2.1) * 0.10 * (0.25 + running)
                addBody(self.shadowPath, r, su, bend, 1.2, su * 0.06, su * 0.09)
                addTail(self.tailPath, r, su, 0.6 + running * 0.6, 0, bend)
                addBody(self.bodyPaths[r.color], r, su, bend, 1.15, 0, 0)
                addFeature(self.earPath, r, su, 0.40, 0.165, 0.085)
                addFeature(self.earPath, r, su, 0.40, -0.165, 0.085)
                addFeature(self.eyePath, r, su, 0.61, 0.075, 0.035)
                addFeature(self.eyePath, r, su, 0.61, -0.075, 0.035)
            end
        end
    end

    self.tailPaint.thickness = base * 0.075
    self.corpseTailPaint.thickness = base * 0.075

    renderer:save()
    renderer:modulateOpacity(self.fade)
    renderer:drawPath(self.bloodDarkPath, self.bloodDarkPaint)
    renderer:drawPath(self.bloodPath, self.bloodPaint)
    renderer:drawPath(self.corpseTailPath, self.corpseTailPaint)
    renderer:drawPath(self.corpsePath, self.corpsePaint)
    renderer:drawPath(self.bellyPath, self.bellyPaint)
    renderer:drawPath(self.corpseEarPath, self.corpseEarPaint)
    renderer:drawPath(self.shadowPath, self.shadowPaint)
    renderer:drawPath(self.tailPath, self.tailPaint)
    for i, p in self.bodyPaths do
        renderer:drawPath(p, self.bodyPaints[i])
    end
    renderer:drawPath(self.earPath, self.earPaint)
    renderer:drawPath(self.eyePath, self.eyePaint)
    renderer:restore()
end

return function(context: Context): Layout<Swarm>
    return {
        hp = 24,
        maxHp = 24,
        ratScale = 1,

        size = Vector.xy(0, 0),
        rats = {},
        order = {},
        aliveCount = 0,
        fade = 1,
        lastHp = -1,
        lastMax = -1,
        lastScale = -1,
        lastW = -1,
        lastH = -1,
        cells = {},

        shadowPath = Path.new(),
        bloodDarkPath = Path.new(),
        bloodPath = Path.new(),
        corpseTailPath = Path.new(),
        corpsePath = Path.new(),
        bellyPath = Path.new(),
        corpseEarPath = Path.new(),
        tailPath = Path.new(),
        bodyPaths = { Path.new(), Path.new(), Path.new() },
        earPath = Path.new(),
        eyePath = Path.new(),

        shadowPaint = Paint.with({ color = Color.rgba(0, 0, 0, 70) }),
        bloodDarkPaint = Paint.with({ color = Color.rgb(120, 8, 12) }),
        bloodPaint = Paint.with({ color = Color.rgb(176, 20, 22) }),
        corpseTailPaint = Paint.with({
            style = 'stroke',
            color = Color.rgb(120, 92, 90),
            thickness = 1,
            cap = 'round',
            join = 'round',
        }),
        corpsePaint = Paint.with({ color = Color.rgb(78, 68, 64) }),
        bellyPaint = Paint.with({ color = Color.rgb(150, 132, 122) }),
        corpseEarPaint = Paint.with({ color = Color.rgb(120, 88, 88) }),
        tailPaint = Paint.with({
            style = 'stroke',
            color = Color.rgb(176, 132, 126),
            thickness = 1,
            cap = 'round',
            join = 'round',
        }),
        bodyPaints = {
            Paint.with({ color = Color.rgb(98, 82, 70) }),
            Paint.with({ color = Color.rgb(122, 108, 96) }),
            Paint.with({ color = Color.rgb(72, 64, 60) }),
        },
        earPaint = Paint.with({ color = Color.rgb(196, 140, 138) }),
        eyePaint = Paint.with({ color = Color.rgb(12, 8, 8) }),

        init = init,
        resize = resize,
        update = update,
        advance = advance,
        draw = draw,
    }
end
