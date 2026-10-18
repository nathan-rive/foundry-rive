-- Flame: a fire built from layered contours whose edges are pushed in and out
-- by noise that scrolls upward, so tongues rise, split and break up. Drawn as a
-- map tile sees it, from above at an angle: the flame stands up the screen from
-- its base at the drawable's origin.
--
-- Inputs:
--   level   0 to 1.5: lit x intensity, eased (0 draws nothing).
--   color   the flame colour; the inner layers lean towards a warm white.
--   flare   trigger: the fire leaps up and settles.
--   size    the flame's width at level 1, in points (it stands about 1.2x as tall).
--   seed    any number: fires with different seeds flicker differently.

type Ember = { x: number, y: number, vx: number, vy: number, age: number, life: number, size: number }

type Flame = {
    level: Input<number>,
    color: Input<Color>,
    flare: Input<Trigger>,
    size: Input<number>,
    seed: Input<number>,

    time: number,
    burst: number,
    spawn: number,
    embers: { Ember },
    paths: { Path },
    emberPath: Path,
    paint: Paint,
    emberPaint: Paint,
}

local TAU = math.pi * 2
local POINTS = 64
local MAX_EMBERS = 24
local WARM_WHITE = Color.rgb(255, 244, 214)

-- Per layer, outermost first: width, height, how far towards warm white,
-- opacity, and how rough the edge is.
local WIDTH = { 1.0, 0.8, 0.56, 0.3 }
local HEIGHT = { 1.0, 0.84, 0.62, 0.36 }
local WHITE = { 0.0, 0.3, 0.62, 0.92 }
local ALPHA = { 0.82, 0.8, 0.86, 1.0 }
local ROUGH = { 1.0, 0.8, 0.55, 0.3 }
-- The outer layers paint normally, so they keep their colour over a light
-- floor; the inner ones are screened on top, for the heat.
local BLEND: { BlendMode } = { "srcOver", "srcOver", "screen", "screen" }
local DARKEN = { 0.18, 0.0, 0.0, 0.0 }
local BLACK = Color.rgb(0, 0, 0)

-- Gradient noise ------------------------------------------------------------

local PERM: { number } = table.create(512, 0)
do
    local p: { number } = table.create(256, 0)
    for i = 1, 256 do
        p[i] = i - 1
    end
    local s = 1337
    for i = 256, 2, -1 do
        s = (s * 16807) % 2147483647
        local j = (s % i) + 1
        p[i], p[j] = p[j], p[i]
    end
    for i = 1, 512 do
        PERM[i] = p[((i - 1) % 256) + 1]
    end
end

local GX = { 1, -1, 1, -1, 1.4142, -1.4142, 0, 0 }
local GY = { 1, 1, -1, -1, 0, 0, 1.4142, -1.4142 }

local function grad(ix: number, iy: number, dx: number, dy: number): number
    local h = PERM[PERM[(ix % 256) + 1] + (iy % 256) + 1] % 8 + 1
    return GX[h] * dx + GY[h] * dy
end

local function fade(t: number): number
    return t * t * t * (t * (t * 6 - 15) + 10)
end

-- Perlin noise, roughly -1 to 1.
local function noise(x: number, y: number): number
    local xi, yi = math.floor(x), math.floor(y)
    local xf, yf = x - xi, y - yi
    local u, v = fade(xf), fade(yf)
    local a = grad(xi, yi, xf, yf)
    local b = grad(xi + 1, yi, xf - 1, yf)
    local c = grad(xi, yi + 1, xf, yf - 1)
    local d = grad(xi + 1, yi + 1, xf - 1, yf - 1)
    local top = a + (b - a) * u
    local bottom = c + (d - c) * u
    return (top + (bottom - top) * v) * 0.7
end

local function fbm(x: number, y: number): number
    return noise(x, y) + 0.5 * noise(x * 2.03, y * 2.03) + 0.3 * noise(x * 4.1, y * 4.1)
        + 0.18 * noise(x * 8.3, y * 8.3)
end

-- Helpers -------------------------------------------------------------------

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

local XS: { number } = table.create(POINTS, 0)
local YS: { number } = table.create(POINTS, 0)

-- A closed curve through XS/YS (Catmull-Rom as cubics).
local function addLoop(path: Path)
    path:moveTo(Vector.xy(XS[1], YS[1]))
    for i = 1, POINTS do
        local i0 = ((i - 2) % POINTS) + 1
        local i2 = (i % POINTS) + 1
        local i3 = ((i + 1) % POINTS) + 1
        local c1x = XS[i] + (XS[i2] - XS[i0]) / 6
        local c1y = YS[i] + (YS[i2] - YS[i0]) / 6
        local c2x = XS[i2] - (XS[i3] - XS[i]) / 6
        local c2y = YS[i2] - (YS[i3] - YS[i]) / 6
        path:cubicTo(Vector.xy(c1x, c1y), Vector.xy(c2x, c2y), Vector.xy(XS[i2], YS[i2]))
    end
    path:close()
end

-- The protocol ----------------------------------------------------------------

local function onFlare(self: Flame)
    self.burst = 1
end

local function advance(self: Flame, seconds: number): boolean
    local dt = math.min(seconds, 0.1)
    self.time += dt
    self.burst = math.max(0, self.burst - dt * 1.2)

    local level = clamp(self.level, 0, 1.5)
    local size = self.size * (0.35 + 0.65 * level)
    local flare = smooth(self.burst)

    -- Embers rise, drift and wink out; new ones spawn with the fire's strength.
    local embers = self.embers
    for i = #embers, 1, -1 do
        local e = embers[i]
        e.age += dt
        if e.age >= e.life then
            table.remove(embers, i)
        else
            e.vx += math.sin(self.time * 3 + e.life * 9) * size * 0.6 * dt
            e.x += e.vx * dt
            e.y += e.vy * dt
        end
    end
    if level > 0.02 then
        self.spawn += dt * (5 + 18 * flare) * math.min(1, level)
        while self.spawn >= 1 and #embers < MAX_EMBERS do
            self.spawn -= 1
            table.insert(embers, {
                x = (math.random() - 0.5) * size * 0.5,
                y = -math.random() * size * 0.5,
                vx = (math.random() - 0.5) * size * 0.4,
                vy = -size * (0.9 + math.random() * 0.9),
                age = 0,
                life = 0.6 + math.random() * 0.9,
                size = 1.2 + math.random() * 1.4,
            })
        end
        self.spawn = math.min(self.spawn, 1)
    end
    return true
end

local function draw(self: Flame, renderer: Renderer)
    local level = clamp(self.level, 0, 1.5)
    if level < 0.01 then
        return
    end
    local strength = math.min(1, level * 4)
    local flare = smooth(self.burst)
    local size = self.size * (0.35 + 0.65 * level)
    local t = self.time
    local seed = self.seed * 17.31
    local sway = math.sin(t * 1.3 + seed) * 0.6 + math.sin(t * 2.9 + seed * 0.7) * 0.4

    local paint = self.paint
    for k = 1, #WIDTH do
        local r = size * 0.5 * WIDTH[k] * (1 + 0.25 * flare)
        local h = size * 1.2 * HEIGHT[k] * (1 + 0.7 * flare)
        local base = r * 0.32
        local rough = size * 0.27 * ROUGH[k] * (1 + 0.6 * flare)
        local layerSeed = seed + k * 3.7
        for i = 1, POINTS do
            local a = (i - 1) / POINTS * TAU
            local ux, up = math.sin(a), math.cos(a)
            local top = math.max(0, up)
            -- The undistorted flame: a teardrop, narrowing into a tongue at the top
            -- and flattened at the base, where it sits on the coals.
            local x = ux * r * (1 - 0.62 * top ^ 1.4)
            local y = if up > 0 then -up * h else -up * base
            -- Noise sampled where the point is, in a field scrolling upward:
            -- bumps on the edge travel up and leave the tip.
            local n = fbm(x / size * 3.2 + layerSeed, y / size * 3.2 + t * 2.8)
            local push = n * rough * (0.35 + 1.4 * top)
            x += ux * push + sway * size * 0.06 * top * top
            y -= top * math.abs(push) * 0.9 + (if up > 0 then up * push * 0.6 else 0)
            XS[i] = x
            YS[i] = y
        end
        local path = self.paths[k]
        path:reset()
        addLoop(path)

        local c = Color.lerp(Color.lerp(self.color, BLACK, DARKEN[k]), WARM_WHITE, WHITE[k])
        paint.blendMode = BLEND[k]
        local alpha = ALPHA[k] * strength
        paint.gradient = Gradient.linear(Vector.xy(0, base), Vector.xy(0, -h * 1.15), {
            { position = 0, color = Color.opacity(c, alpha) :: Color },
            { position = 0.45, color = Color.opacity(c, alpha * 0.9) :: Color },
            { position = 1, color = Color.opacity(c, 0) :: Color },
        })
        renderer:drawPath(path, paint)
    end

    -- Embers.
    local ep = self.emberPath
    ep:reset()
    for _, e in self.embers do
        local s = e.size * (1 - e.age / e.life)
        if s > 0.2 then
            local k = s * 0.5523
            ep:moveTo(Vector.xy(e.x + s, e.y))
            ep:cubicTo(Vector.xy(e.x + s, e.y + k), Vector.xy(e.x + k, e.y + s), Vector.xy(e.x, e.y + s))
            ep:cubicTo(Vector.xy(e.x - k, e.y + s), Vector.xy(e.x - s, e.y + k), Vector.xy(e.x - s, e.y))
            ep:cubicTo(Vector.xy(e.x - s, e.y - k), Vector.xy(e.x - k, e.y - s), Vector.xy(e.x, e.y - s))
            ep:cubicTo(Vector.xy(e.x + k, e.y - s), Vector.xy(e.x + s, e.y - k), Vector.xy(e.x + s, e.y))
            ep:close()
        end
    end
    self.emberPaint.color = Color.opacity(Color.lerp(self.color, WARM_WHITE, 0.55), 0.9 * strength) :: Color
    renderer:drawPath(ep, self.emberPaint)
end

return function(): Node<Flame>
    return {
        level = 1,
        color = Color.rgb(255, 122, 26),
        flare = onFlare,
        size = 120,
        seed = 0,

        time = 0,
        burst = 0,
        spawn = 0,
        embers = {},
        paths = { Path.new(), Path.new(), Path.new(), Path.new() },
        emberPath = Path.new(),
        paint = Paint.with({ style = "fill", blendMode = "screen" }),
        emberPaint = Paint.with({ style = "fill", blendMode = "screen", color = WARM_WHITE }),

        advance = advance,
        draw = draw,
    }
end
