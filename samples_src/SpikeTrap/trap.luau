--!strict
-- SpikeTrap: a procedural cobblestone trapdoor over a spiked pit.
--
-- A Layout script that fills the artboard. Everything is generated from the
-- size the layout hands it, at a constant density: cobbles are ~stoneSize
-- across and spikes ~spikeSpacing apart, so doubling the area roughly doubles
-- how many there are rather than making them bigger.
--
-- The state machine animates two keyed inputs:
--   reveal    0 = hidden (faint outlines only)
--             1 = revealed (solid stones; the pit shows through the seams)
--   collapse  0 = floor intact
--             1 = every stone has fallen into the pit
-- `collapse` is turned into a staggered, stone-by-stone fall here, so playing
-- it backwards makes the stones float back up and reform the floor.

type Stone = {
    x: number,
    y: number,
    path: Path,
    halfW: number,
    halfH: number,
    base: Color,
    light: Color,
    delay: number,
    spin: number,
}

type SpikeRow = {
    shadow: Path,
    dark: Path,
    light: Path,
    blood: Path,
}

type Quad = { path: Path, from: Vector, to: Vector, a: Color, b: Color }

type Trap = {
    reveal: Input<number>,
    collapse: Input<number>,
    stoneSize: Input<number>,
    spikeSpacing: Input<number>,
    seed: Input<number>,

    size: Vector,
    dirty: boolean,
    lastReveal: number,
    lastCollapse: number,

    stones: { Stone },
    rows: { SpikeRow },
    walls: { Quad },
    lip: Quad?,
    bounds: Path,
    floor: Path,
    floorMin: Vector,
    floorMax: Vector,

    paint: Paint,
    grad: Paint,
    stroke: Paint,
}

-- Fraction of the whole collapse that a single stone spends falling. The rest
-- of the timeline is spent staggering their start times.
local FALL = 0.32

----------------------------------------------------------------------------
-- helpers

local function rand(i: number, j: number, k: number): number
    local v = math.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return v - math.floor(v)
end

local function clamp01(v: number): number
    if v < 0 then
        return 0
    elseif v > 1 then
        return 1
    end
    return v
end

local function smooth(a: number, b: number, v: number): number
    local t = clamp01((v - a) / (b - a))
    return t * t * (3 - 2 * t)
end

local function gray(v: number): Color
    local c = math.floor(clamp01(v) * 255 + 0.5)
    return Color.rgb(c, c, c)
end

-- The same colour with its alpha scaled by `a`.
local function fade(c: Color, a: number): Color
    local alpha = Color.alpha(c) :: number
    return Color.alpha(c, math.floor(alpha * clamp01(a) + 0.5)) :: Color
end

local function rgb(r: number, g: number, b: number): Color
    return Color.rgb(math.floor(r + 0.5), math.floor(g + 0.5), math.floor(b + 0.5))
end

-- Path:quadTo does not render in current runtimes, so emit the equal cubic.
local function quad(path: Path, from: Vector, ctrl: Vector, to: Vector)
    path:cubicTo(from + (ctrl - from) * (2 / 3), to + (ctrl - to) * (2 / 3), to)
end

-- Polygons are wound clockwise on screen (y down), as the clockwise fill
-- rule that script paths use requires.
local function poly(points: { Vector }): Path
    local path = Path.new()
    path:moveTo(points[1])
    for i = 2, #points do
        path:lineTo(points[i])
    end
    path:close()
    return path
end

----------------------------------------------------------------------------
-- generation

-- An irregular, rounded cobble centred on the origin.
local function stonePath(hw: number, hh: number, r: number, c: number, s: number): Path
    local m = math.min(hw, hh)
    local function corner(n: number): number
        return m * (0.06 + 0.18 * rand(r, c, s + n))
    end
    local function bulge(n: number): number
        return m * 0.12 * (rand(r, c, s + n) - 0.3)
    end
    local pts: { Vector } = {
        Vector.xy(-hw + corner(1), -hh + corner(2)),
        Vector.xy((rand(r, c, s + 3) - 0.5) * hw * 0.6, -hh - bulge(4)),
        Vector.xy(hw - corner(5), -hh + corner(6)),
        Vector.xy(hw + bulge(7), (rand(r, c, s + 8) - 0.5) * hh * 0.6),
        Vector.xy(hw - corner(9), hh - corner(10)),
        Vector.xy((rand(r, c, s + 11) - 0.5) * hw * 0.6, hh + bulge(12)),
        Vector.xy(-hw + corner(13), hh - corner(14)),
        Vector.xy(-hw - bulge(15), (rand(r, c, s + 16) - 0.5) * hh * 0.6),
    }
    local n = #pts
    local path = Path.new()
    local cur = (pts[n] + pts[1]) * 0.5
    path:moveTo(cur)
    for i = 1, n do
        local to = (pts[i] + pts[(i % n) + 1]) * 0.5
        quad(path, cur, pts[i], to)
        cur = to
    end
    path:close()
    return path
end

local function buildStones(self: Trap, w: number, h: number, seed: number)
    local unit = math.max(8, self.stoneSize)
    local gap = math.max(1.5, math.min(4, unit * 0.09))
    local rowsN = math.max(1, math.floor(h / unit + 0.5))
    local colsN = math.max(1, math.floor(w / unit + 0.5))
    local rowH = h / rowsN
    local colW = w / colsN
    local cx = w * 0.5
    local cy = h * 0.5
    local maxD = math.sqrt(cx * cx + cy * cy)

    for r = 0, rowsN - 1 do
        -- Every row starts at a random offset so seams never line up, and
        -- cells are merged at random into wider stones.
        local offset = rand(r, 0, seed + 30)
        local c = 0
        local count = colsN + 1
        while c < count do
            local span = if rand(r, c, seed + 31) < 0.35 then 2 else 1
            local x0 = math.max(0, (c - offset) * colW)
            local x1 = math.min(w, (c + span - offset) * colW)
            local hw = (x1 - x0) * 0.5 - gap * 0.5
            local hh = rowH * 0.5 - gap * 0.5
            if hw > math.min(3, unit * 0.15) and hh > 1 then
                local x = (x0 + x1) * 0.5
                local y = (r + 0.5) * rowH
                local shade = rand(r, c, seed + 20)
                local warm = rand(r, c, seed + 21) * 14
                local base = rgb(92 + shade * 46 + warm, 86 + shade * 40 + warm * 0.6, 78 + shade * 34)
                local dist = math.sqrt((x - cx) ^ 2 + (y - cy) ^ 2) / maxD
                local order = clamp01(0.55 * rand(r, c, seed + 22) + 0.45 * dist)
                table.insert(self.stones, {
                    x = x,
                    y = y,
                    path = stonePath(hw, hh, r, c, seed * 31),
                    halfW = hw,
                    halfH = hh,
                    base = base,
                    light = Color.lerp(base, Color.rgb(236, 230, 216), 0.38),
                    delay = order * (1 - FALL),
                    spin = (rand(r, c, seed + 23) - 0.5) * 1.8,
                })
            end
            c += span
        end
    end
end

-- The pit, seen slightly from above and in front: the far wall is tall, the
-- side walls narrow, and the near lip only a sliver.
local function buildPit(self: Trap, w: number, h: number)
    local depth = math.max(6, math.min(60, math.min(w, h) * 0.16))
    local fx0 = depth * 0.42
    local fx1 = w - depth * 0.42
    local fy0 = depth
    local fy1 = h - depth * 0.18
    self.floorMin = Vector.xy(fx0, fy0)
    self.floorMax = Vector.xy(fx1, fy1)

    local tl = Vector.xy(0, 0)
    local tr = Vector.xy(w, 0)
    local br = Vector.xy(w, h)
    local bl = Vector.xy(0, h)
    local ftl = Vector.xy(fx0, fy0)
    local ftr = Vector.xy(fx1, fy0)
    local fbr = Vector.xy(fx1, fy1)
    local fbl = Vector.xy(fx0, fy1)

    self.bounds = poly({ tl, tr, br, bl })
    self.floor = poly({ ftl, ftr, fbr, fbl })
    self.walls = {
        -- far wall: lit from above, falling into darkness at the floor
        {
            path = poly({ tl, tr, ftr, ftl }),
            from = Vector.xy(0, 0),
            to = Vector.xy(0, fy0),
            a = Color.rgb(84, 74, 63),
            b = Color.rgb(16, 13, 11),
        },
        -- left wall
        {
            path = poly({ tl, ftl, fbl, bl }),
            from = Vector.xy(0, 0),
            to = Vector.xy(fx0, 0),
            a = Color.rgb(58, 50, 43),
            b = Color.rgb(12, 10, 9),
        },
        -- right wall
        {
            path = poly({ tr, br, fbr, ftr }),
            from = Vector.xy(w, 0),
            to = Vector.xy(fx1, 0),
            a = Color.rgb(46, 40, 34),
            b = Color.rgb(10, 8, 7),
        },
    }
    -- near lip: drawn over the spikes, it is the edge they stand behind
    self.lip = {
        path = poly({ fbl, fbr, br, bl }),
        from = Vector.xy(0, h),
        to = Vector.xy(0, fy1),
        a = Color.rgb(40, 34, 29),
        b = Color.rgb(8, 7, 6),
    }
end

local function buildSpikes(self: Trap, seed: number)
    local spacing = math.max(6, self.spikeSpacing)
    local x0 = self.floorMin.x
    local y0 = self.floorMin.y
    local fw = self.floorMax.x - x0
    local fh = self.floorMax.y - y0
    if fw <= 1 or fh <= 1 then
        return
    end
    local cols = math.max(1, math.floor(fw / spacing + 0.5))
    local rows = math.max(1, math.floor(fh / spacing + 0.5))
    local cellW = fw / cols
    local cellH = fh / rows
    local k = seed * 7 + 1000

    for r = 0, rows - 1 do
        local row: SpikeRow = {
            shadow = Path.new(),
            dark = Path.new(),
            light = Path.new(),
            blood = Path.new(),
        }
        for c = 0, cols - 1 do
            local x = x0 + (c + 0.5 + (rand(r, c, k) - 0.5) * 0.6) * cellW
            local y = y0 + (r + 0.7 + (rand(r, c, k + 1) - 0.5) * 0.4) * cellH
            local height = spacing * (0.95 + 0.55 * rand(r, c, k + 2))
            local rad = spacing * (0.17 + 0.08 * rand(r, c, k + 3))
            local lean = (rand(r, c, k + 4) - 0.5) * 0.3 * height
            local tip = Vector.xy(x + lean, y - height)
            local left = Vector.xy(x - rad, y)
            local right = Vector.xy(x + rad, y)
            local front = Vector.xy(x + rad * 0.15, y + rad * 0.35)

            -- shadow cast toward the bottom right
            row.shadow:moveTo(left)
            row.shadow:lineTo(Vector.xy(x + height * 0.55, y + height * 0.3))
            row.shadow:lineTo(right)
            quad(row.shadow, right, Vector.xy(x, y + rad * 0.7), left)
            row.shadow:close()

            -- lit face
            row.light:moveTo(left)
            row.light:lineTo(tip)
            row.light:lineTo(front)
            quad(row.light, front, Vector.xy(x - rad * 0.6, y + rad * 0.4), left)
            row.light:close()

            -- shaded face
            row.dark:moveTo(tip)
            row.dark:lineTo(right)
            quad(row.dark, right, Vector.xy(x + rad * 0.7, y + rad * 0.35), front)
            row.dark:close()

            if rand(r, c, k + 5) < 0.2 then
                row.blood:moveTo(tip)
                row.blood:lineTo(tip + (right - tip) * 0.35)
                row.blood:lineTo(tip + (left - tip) * 0.35)
                row.blood:close()
            end
        end
        table.insert(self.rows, row)
    end
end

local function rebuild(self: Trap)
    self.dirty = false
    self.stones = {}
    self.rows = {}
    self.walls = {}
    self.lip = nil
    local w = self.size.x
    local h = self.size.y
    if w <= 1 or h <= 1 then
        return
    end
    local seed = math.floor(self.seed)
    buildPit(self, w, h)
    buildStones(self, w, h, seed)
    buildSpikes(self, seed)
end

----------------------------------------------------------------------------
-- drawing

local function drawQuad(self: Trap, renderer: Renderer, q: Quad, alpha: number)
    local grad = self.grad
    grad.gradient = Gradient.linear(q.from, q.to, {
        { position = 0, color = fade(q.a, alpha) },
        { position = 1, color = fade(q.b, alpha) },
    })
    renderer:drawPath(q.path, grad)
end

-- `alpha` fades the pit in; it is lit by however much floor has fallen away.
local function drawPitHole(self: Trap, renderer: Renderer, alpha: number, collapse: number)
    local w = self.size.x
    local h = self.size.y
    local grad = self.grad
    local stroke = self.stroke

    renderer:save()
    renderer:modulateColor(gray(0.45 + 0.55 * collapse))

    grad.gradient = Gradient.radial(Vector.xy(w * 0.5, h * 0.6), math.max(w, h) * 0.6, {
        { position = 0, color = fade(Color.rgb(48, 38, 31), alpha) },
        { position = 1, color = fade(Color.rgb(12, 10, 9), alpha) },
    })
    renderer:drawPath(self.floor, grad)

    for _, wall in self.walls do
        drawQuad(self, renderer, wall, alpha)
    end

    -- soft shadow where the floor meets the walls
    stroke.thickness = math.max(4, math.min(w, h) * 0.05)
    stroke.feather = stroke.thickness * 1.5
    stroke.color = Color.rgba(0, 0, 0, math.floor(200 * alpha))
    renderer:drawPath(self.floor, stroke)
    stroke.feather = 0
    renderer:restore()
end

local function drawPitContents(self: Trap, renderer: Renderer, alpha: number, collapse: number)
    local paint = self.paint
    renderer:save()
    renderer:modulateColor(gray(0.45 + 0.55 * collapse))
    for _, row in self.rows do
        paint.color = Color.rgba(0, 0, 0, math.floor(110 * alpha))
        renderer:drawPath(row.shadow, paint)
        paint.color = fade(Color.rgb(58, 56, 55), alpha)
        renderer:drawPath(row.dark, paint)
        paint.color = fade(Color.rgb(198, 194, 184), alpha)
        renderer:drawPath(row.light, paint)
        paint.color = fade(Color.rgb(118, 20, 16), alpha)
        renderer:drawPath(row.blood, paint)
    end

    local lip = self.lip
    if lip then
        drawQuad(self, renderer, lip, alpha)
    end
    renderer:restore()
end

-- `t` is this stone's own fall progress, `reveal` how solid stones are.
-- (Opacity is applied through paint colours: Renderer:modulateOpacity darkens
-- rather than fades in current runtimes.)
local function drawStone(self: Trap, renderer: Renderer, stone: Stone, t: number, reveal: number)
    local e = t * t -- gravity: slow to start, fast to finish
    local w = self.size.x
    local h = self.size.y
    -- a little hop as the stone breaks free, then it shrinks away (falls)
    local scale = (1 - 0.82 * e) * (1 + 0.07 * math.sin(math.pi * math.min(1, t * 4)))
    local x = stone.x + (w * 0.5 - stone.x) * 0.12 * e
    local y = stone.y + (h * 0.5 - stone.y) * 0.12 * e + e * stone.halfH * 0.6
    local vanish = 1 - smooth(0.8, 1, t)

    renderer:save()
    renderer:transform(
        Mat2D.withTranslation(x, y) * Mat2D.withRotation(stone.spin * e) * Mat2D.withScale(scale, scale)
    )
    renderer:modulateColor(gray(1 - 0.8 * e))

    local paint = self.paint
    local stroke = self.stroke
    local solid = reveal * vanish
    if solid > 0.001 then
        -- the drop shadow only lands once the stone is (nearly) solid
        renderer:save()
        renderer:transform(Mat2D.withTranslation(1.2, 1.8))
        paint.color = Color.rgba(0, 0, 0, math.floor(150 * solid * reveal * reveal))
        renderer:drawPath(stone.path, paint)
        renderer:restore()

        paint.color = fade(stone.base, solid)
        renderer:drawPath(stone.path, paint)

        renderer:save()
        renderer:transform(
            Mat2D.withTranslation(-stone.halfW * 0.07, -stone.halfH * 0.1) * Mat2D.withScale(0.76, 0.7)
        )
        paint.color = fade(stone.light, 0.45 * solid)
        renderer:drawPath(stone.path, paint)
        renderer:restore()
    end

    -- Outlines: all that is visible while hidden. A dark line and a faint
    -- light one, so the patch can be spotted on dark and light maps alike.
    local hidden = 1 - reveal
    stroke.feather = 0
    stroke.thickness = 1.6
    stroke.color = Color.rgba(255, 246, 225, math.floor(255 * 0.16 * hidden * vanish))
    renderer:save()
    renderer:transform(Mat2D.withTranslation(0.9, 0.9))
    renderer:drawPath(stone.path, stroke)
    renderer:restore()
    stroke.thickness = 1.2
    stroke.color = Color.rgba(20, 16, 13, math.floor(255 * (0.3 + 0.45 * reveal) * vanish))
    renderer:drawPath(stone.path, stroke)

    -- arcane glow while the stone is in flight
    if t > 0 and t < 1 then
        local glow = math.sin(math.pi * math.min(1, t * 1.6)) * (1 - e)
        stroke.thickness = 1.2
        stroke.feather = 2
        stroke.color = Color.rgba(140, 215, 255, math.floor(255 * 0.38 * glow))
        renderer:drawPath(stone.path, stroke)
        stroke.feather = 0
    end
    renderer:restore()
end


----------------------------------------------------------------------------
-- protocol

function init(self: Trap, context: Context): boolean
    return true
end

function resize(self: Trap, size: Vector, scale: number)
    if size.x ~= self.size.x or size.y ~= self.size.y then
        self.size = size
        self.dirty = true
    end
end

function update(self: Trap)
    -- an input changed; the geometry inputs need a rebuild
    self.dirty = true
end

function advance(self: Trap, seconds: number): boolean
    return self.dirty or self.reveal ~= self.lastReveal or self.collapse ~= self.lastCollapse
end

function draw(self: Trap, renderer: Renderer)
    if self.dirty then
        rebuild(self)
    end
    self.lastReveal = self.reveal
    self.lastCollapse = self.collapse
    if #self.stones == 0 then
        return
    end
    local reveal = clamp01(self.reveal)
    local collapse = clamp01(self.collapse)
    -- Stones turn solid first and the pit fades in behind them, so a fade
    -- never shows a dark hole through half-transparent stones.
    local stonesIn = smooth(0, 0.6, reveal)
    local pitIn = smooth(0.35, 1, reveal)

    renderer:save()
    renderer:clipPath(self.bounds)

    local pit = pitIn > 0.001
    if pit then
        drawPitHole(self, renderer, pitIn, collapse)
    end

    -- Stones far into their fall are below the spike tips, so draw them first.
    local SUNK = 0.55
    if collapse > 0 then
        for _, stone in self.stones do
            local t = clamp01((collapse - stone.delay) / FALL)
            if t >= SUNK and t < 1 then
                drawStone(self, renderer, stone, t, stonesIn)
            end
        end
    end

    if pit then
        drawPitContents(self, renderer, pitIn, collapse)
    end

    for _, stone in self.stones do
        local t = clamp01((collapse - stone.delay) / FALL)
        if t < SUNK then
            drawStone(self, renderer, stone, t, stonesIn)
        end
    end

    -- a rusty frame marks the revealed trap; it fades once the floor is gone
    local stroke = self.stroke
    stroke.thickness = 3
    stroke.feather = 0
    stroke.color = Color.rgba(150, 62, 30, math.floor(255 * 0.85 * reveal * (1 - 0.7 * collapse)))
    renderer:drawPath(self.bounds, stroke)

    renderer:restore()
end

return function(context: Context): Layout<Trap>
    return {
        reveal = 0,
        collapse = 0,
        stoneSize = 28,
        spikeSpacing = 22,
        seed = 1,

        size = Vector.xy(0, 0),
        dirty = true,
        lastReveal = -1,
        lastCollapse = -1,

        stones = {},
        rows = {},
        walls = {},
        lip = nil,
        bounds = Path.new(),
        floor = Path.new(),
        floorMin = Vector.xy(0, 0),
        floorMax = Vector.xy(0, 0),

        paint = Paint.with({ style = 'fill' }),
        grad = Paint.with({ style = 'fill' }),
        stroke = Paint.with({ style = 'stroke', join = 'round', cap = 'round' }),

        init = init,
        resize = resize,
        update = update,
        advance = advance,
        draw = draw,
    }
end
