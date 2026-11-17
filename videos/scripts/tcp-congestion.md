# How fast may I send? TCP feels for a limit nobody tells it

- Slug / scene: `tcp-congestion`, `videos/scenes/tcp_congestion.py:TcpCongestion`
- Lesson: `net-08`, section 2, "Congestion control: the sender guesses what the road can take"
- Audience / level: a complete newcomer who has met the lesson's van picture (several vans on the road at once,
  each signed note frees a place, speed = window per round trip) and the receiver's room (flow control).
- Length: 4:40 (~760 words of narration at the Kokoro voice's ~180 words a minute, plus the guesses and the
  silent chart builds)
- Poster: `POSTER=207` (the full sawtooth, the average line and the readout renamed "congestion window")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: the shop says how much room it has, but nobody says how much the road can take. So
  how many vans should the warehouse send?
- Misconception to steelman and break: "if parcels get lost, just send them again, as fast as before". Broken by
  the full car park (resends join the jam) and by October 1986 (32 kbit/s to 40 bit/s).
- Concept chain: a shared road with a bottleneck and a queue → too much means loss → resending harder makes it worse
  → the sender keeps its own guess and treats loss as the signal → slow start doubles → overflow → three duplicate
  ACKs, resend, halve → +1 per round trip → the sawtooth (AIMD, the congestion window) → costs and real versions
- Analogy family: the lesson's vans. A warehouse (sender) sends vans (segments) to a shop (receiver); signed notes
  (ACKs) come back; a narrow bridge (the bottleneck link) with a small car park (the router's queue); vans turned
  away (dropped packets).
- Open loops: "how many vans should it send?" planted in scene 1 → answered in scene 8; "nobody says how much the
  road can take" → the sender feels for it (scene 4) → the moral.
- Assumptions: the numbers are the lesson's stepper (Reno on a path that holds 100 segments: 10, 20, 40, 80, 160;
  halve to 80; +1 to 100; 101 halves to 50; about three quarters on average), its 1986 figures and its lab result
  (10 MB in about 2 s with no loss, about 20 s with 1% loss). How the 100 splits between the road and the car park
  is drawn for the picture only (70 and 30).

## The one picture

Top: the warehouse (blue, left) and the shop (green, right). Between them, a road of 100 slots, the last 30 of them
a car park in front of a narrow bridge. Vans (blue blocks) fill the slots from the warehouse end; vans that don't fit
show as red blocks above the car park, "turned away". Signed notes (green dots) run back along a lane under the road.
Bottom: a chart of the guess for each round trip, with a dashed line at 100, drawn as the rounds pass. The readout
"the guess" sits by the warehouse. Same places and colours throughout.

## Scene 1 · The question · 0:00–0:30 · [FAMILIAR] [QUESTION] [LOOP-PLANT]

VO: A warehouse sends parcels by van to a shop far away. It doesn't wait for each van to come back. It keeps several
on the road at once, and each signed note from the shop frees a place for one more. In TCP, the vans are segments,
its packets, and how many may be out at once is the window. More vans, more speed. The shop says how much room it
has. But nobody says how much the road can take. So how many vans should the warehouse send?

SCREEN: Warehouse, shop, the road. Ten vans fill the first slots; green notes run back. A map builds in the centre,
one line per mapping: "a van = a segment, one TCP packet", "a signed note = an ACK", "vans out at once = the
window" (with a brace over the ten vans).

## Scene 2 · The bridge · 0:30–1:04 · [ANALOGY] [MAP]

VO: Somewhere on the way is the narrowest part, the bottleneck. Picture a narrow bridge, with a small car park in
front of it. Vans that arrive faster than the bridge lets them over wait in the car park. When the car park is full,
the next vans are turned away, and their parcels are lost. In a network, the bridge is the slowest link on the path.
The car park is the queue in the router in front of it, a waiting area for packets. And turned away means dropped.
Here, the road and the car park together hold 100 vans. The warehouse doesn't know that number.

SCREEN: The bridge and the car park draw in at the road's far end. The map gains "the bridge = the slowest link on
the path", "the car park = the router's queue", "turned away = dropped", each as it is said. A brace under the road
and car park: "together they hold 100". The map stays through scene 3 and clears when the chart arrives.

## Scene 3 · The obvious fix, broken · 1:04–1:41 · [BREAK] [JOKE:pivot]

VO: So parcels get lost. The obvious fix: send them again, just as fast. But the car park is already full.
Resending at the same speed only adds more vans to the jam. In October 1986, the early internet did exactly that. A
link between two university sites at Berkeley fell from 32 kilobits a second to 40 bits a second. Bits, not
kilobits. That's called congestion collapse. The fix came from Van Jacobson, no relation to our vans. It's called
congestion control, and it's been part of TCP since the late 1980s.

SCREEN: The road full, red vans above the car park, and more red vans joining. Caption: "October 1986: 32 kbit/s →
40 bit/s". Then the jam clears for the fix.

## Scene 4 · A guess that grows · 1:41–2:18 · [WISH] [SHRINK] [SHOW] [NAME] [JOKE:is-the-explanation]

VO: The idea: the sender keeps its own guess of how much the road can take, and never has more on the road than that
guess, or the shop's room, whichever is smaller. Nobody tells it the right number. So it tries, and it treats a lost
parcel as the signal that it went too far. A new connection starts small, at 10 segments, about 14 kilobytes on
Linux. Each signed note that comes back adds one more. So 10 out means 10 notes back, and 20 next time. Then 40, then
80. The guess doubles every round trip. This is called slow start. Nobody promised the names would be honest.

SCREEN: "the guess" readout by the warehouse; the chart's axes and the dashed 100 line appear. Each round: vans fill,
notes run back, the readout and the chart step up 10, 20, 40, 80.

## Scene 5 · Predict the overflow · 2:18–2:35 · [PREDICT] [PAUSE] [SHOW]

VO: 80 still fits in 100. Next round, it doubles again. What happens? Pause and guess.

(three seconds)

160 vans. 100 fit on the road and in the car park. The other 60 are turned away.

SCREEN: Countdown. Then 100 slots full and 60 red vans above the car park; the chart's dot at 160 in red.

## Scene 6 · The signal, and the halving · 2:35–3:12 · [SHOW]

VO: How does the warehouse find out? The parcels behind the lost ones still arrive. So the shop keeps sending the
same note: I'm still missing the one after this. Three repeats of the same note, three duplicate ACKs, say exactly one
parcel went missing. The sender resends it at once, which is called fast retransmit. And it cuts its guess in half, to 80.
Above that point, it grows gently: one more segment per round trip. Twenty round trips later, it's back at 100. At
101, the car park overflows again, and the guess drops by half, to 50. Then up by one, down by half, again and again.

SCREEN: Three gold notes run back; "the same note, three times: one parcel is missing". A gold van runs (the resend).
The readout and chart drop to 80, then climb by one per round to 100, overflow at 101, drop to 50, and keep going.

## Scene 7 · Names, and the worse case · 3:12–3:37 · [NAME]

VO: The pattern has a name: additive increase, multiplicative decrease. Add one at a time, cut in half at once. The
sender's guess is the congestion window. On the chart, it draws a sawtooth. On average, it sits at about three
quarters of what the road holds. And if nothing comes back at all, not even a repeat, that's worse news. The guess
drops to 1, and slow start begins again.

SCREEN: Captions name the pattern; the readout's label becomes "congestion window". A dashed average line at 75.

## Scene 8 · Two warnings · 3:37–4:09 · [GUARDRAIL] [JOKE:reward]

VO: Two warnings. First, Linux doesn't run this plain version, called Reno. Its default since 2006 is CUBIC, which
cuts to 70 percent, not half, and grows back along a curve. Same idea, a flatter sawtooth. Second, loss is expensive.
On the lab network, with a 50 millisecond delay, a 10 megabyte download took about 2 seconds. With one packet in a
hundred dropped, it took about 20. So when a fast line feels slow, look for loss before you buy a bigger road.

SCREEN: Captions; the three drops on the chart circled.

## Scene 9 · The moral, and a check · 4:09–4:40 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, how many vans? The sender can't see the road. It feels for the limit: grow until a parcel is lost, cut in
half, and grow again. Everyone sharing the road does the same, and that's what keeps it moving. One quick check. The guess
is 90 when three duplicate ACKs arrive. What is it next? Pause and think.

(three seconds)

45. Half of 90. Then it climbs by one each round trip.

SCREEN: The sawtooth glows; "grow until a loss, halve, grow again" (the caption keeps the short word). The readout shows 90 and "?", a countdown, then 45.

---

### Beat check

- FAMILIAR first (the vans the viewer met in section 0), then the QUESTION (scene 1).
- ANALOGY + MAP said out loud (scene 2), before any formal name.
- BREAK of the obvious fix, resend just as fast, with the 1986 collapse (scene 3).
- PREDICT with PAUSE (scene 5, and the check in scene 9); SHOW right after each.
- NAME after the behaviour is seen: slow start (scene 4, after the doubling), fast retransmit and duplicate ACKs
  (scene 6), additive increase / multiplicative decrease and the congestion window (scene 7).
- GUARDRAIL (scene 8): real Linux uses CUBIC, and loss is expensive. MORAL last.
- Light moments: no relation to our vans (~1:33), honest names (~2:15), a bigger road (~4:05).
- Where the van picture breaks is not spelled out; it holds for the whole video (vans, notes, car park), and the
  accuracy notes list what it leaves out.

### Accuracy notes for the producer

- The numbers are the lesson's Reno stepper on a path that holds 100 segments. Real slow start can overshoot further
  within one round trip; the lab's Try it saw 359 against a path of 186.
- The 70/30 split between road and car park is only for the picture; the lesson says the path holds 100 counting what
  is on the link and what the bottleneck router can queue.
- The threshold where growth turns gentle is ssthresh; the video says "above that point" and shows 80.
- On a timeout, Reno sets ssthresh to half the window and the window to 1; the video says the guess drops to 1 and
  slow start begins again.
- CUBIC's 70% and its curve, BBR, and the receive window's part in "whichever is smaller" are in the lesson. BBR is
  left out of the video.
- The 1986 figures (Berkeley, 32 kbit/s to 40 bit/s) and the lab result (10 MB, 50 ms delay, about 2 s vs about
  20 s at 1% loss, three runs each) are the lesson's.
