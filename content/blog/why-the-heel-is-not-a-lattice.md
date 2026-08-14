---
title: Why the heel is not a lattice
date: 2026-08-14
summary: An open honeycomb is the stiffest thing you can build in compression and the weakest thing you can build for holding a heel in place. Here is the arithmetic that made us close it up.
tags: geometry, engineering, drop-001
---

Every printed insert you have seen photographed is an open lattice, all the way
through, heel to toe. It photographs beautifully. We built one, measured it, and
then closed the heel.

Here is why.

## A honeycomb is a bundle of tubes

Load a vertical-walled honeycomb straight down its axis and it is the stiffest
structure you can make out of a given amount of material. That sounds like an
argument for using it. It is the opposite.

A heel cup does not work by resisting downward load. It works by resisting the
heel **splaying sideways**. A honeycomb cell is a tube, and tubes splay. Push a
tube over and it hinges at its base. So an open-lattice heel cup gives you the
one property you did not need and none of the property you did.

## The wall that crushes on the second step

The other half is fatigue. A thin wall in a lattice does not fail by breaking,
it fails by **buckling** — and once a TPU wall has creased, it creases in the
same place forever.

Plate buckling for a wall of thickness `t` braced by its neighbours at spacing
`b`:

```
σ_crit ≈ 4π²E / (12(1−ν²)) · (t/b)²
```

Taking E for TPU 95A at 20 MPa — an estimate, it moves with print orientation,
layer bonding and moisture — and a peak heel-strike pressure around 600 kPa:

| zone | wall | solid fraction | σ_crit | σ in the wall | margin |
|---|---|---|---|---|---|
| 0.86 mm lattice heel | 0.86 mm | 20 % | 2.7 MPa | 3.0 MPa | **buckles** |
| 2.40 mm heel | 2.40 mm | 48 % | 19.3 MPa | 1.25 MPa | 15× |
| 0.86 mm forefoot | 0.86 mm | 25 % | 4.5 MPa | 2.4 MPa | 1.9× |

The first row is the interesting one. A 0.86 mm wall — two extrusions at a
0.4 mm nozzle, which is the thinnest honest wall on that machine — goes over at
heel strike. For about a week that reads as *cushioning*. After that it is a
crease, and then it is a crack.

The forefoot row is the reason the forefoot stays open. Push-off never reaches
the same peak, the margin holds, and that is exactly where the honeycomb is
earning its keep: flex, moisture, airflow.

## What we did instead

The heel is solid. The cup crest is solid. The honeycomb is a field of recessed
pockets in the top surface rather than holes through the part, and the wall
thickness is graded along the foot so there is no seam anywhere for the two
behaviours to delaminate at.

Measured off the shipped mesh, US Men's 11:

| | |
|---|---|
| overall | 290.0 × 98.0 × 14.17 mm |
| heel floor → cup crest | 5.6 → 13.9 mm (**8.1 mm cup**) |
| arch, medial / centre / lateral | 10.8 / 7.8 / 4.6 mm |
| forefoot section | 3.4–3.9 mm |
| pocket pitch | 6.4–8.6 mm |
| land between pockets | 1.6 mm |
| volume · mass in TPU 95A | 104.9 cm³ · ≈127 g |

## The part we got wrong first

We shipped a revision with a heel cup taken from the wrong file — a ridge with
its crest 11–15 mm inboard, behind a flat flange. It is a real orthotic pattern.
It is not ours.

The cup we actually wear peaks **at the perimeter**: 12.0 mm on the lateral side
and 12.7 mm on the medial against a 3.1 mm floor, with the rise starting about
16 mm from centre. We had measured that off our own insert and then designed
past it. The current cup is that geometry, scaled.

That is the whole method, really. Build it, measure the thing you actually
built, and believe the measurement over the intention.
