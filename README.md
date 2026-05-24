![no AI was used in the production of this repo](docs/images/gemini_made_this_for_me.png)

# stupid_scripts

Personal Linux helper scripts, shell config, and desktop glue.

This is not a framework; it is an example of slowly turning personal Linux annoyances into small scripts you can understand, modify, and recover later.

This repo exists so my useful little Linux scripts are not scattered across `~/bin`, `~/.local/bin`, random GNOME settings, and whatever other nonsense I did at 2 AM.

It is basically a tiny recovery kit for my desktop workflow. Well, portions of my desktop workflow. Portions that are unique to my Pop!_OS install. And that's important sometimes.

## Purpose

This is the source of truth for small local scripts I actually use.

Runtime commands should live in:

```text
~/.local/bin
```

But the real editable files live in this repo:

```bash
~/repos/stupid_scripts
```

Most/all things in ~/.local/bin should be symlinks back into this repo.

## QUIC restore

Fresh Linux install, SSD died, or I did something brave and stupid:

```bash
mkdir -p ~/repos
cd ~/repos
git clone git@github.com:kain2749/stupid_scripts.git
cd stupid_scripts
./install.sh
source ~/.bashrc
```
ha, see what i did there with quic

Then verify:

```bash
command -v toggle-audio
command -v gnome-status-line
command -v dock-favs
command -v dock-favs-policy
ls -l ~/.bash_aliases
```
## Layout

```text
stupid_scripts/
├── bin/
│   ├── dock-favs
│   ├── dock-favs-policy
│   ├── gnome-status-line
│   └── toggle-audio
├── shell/
│   ├── bash_aliases
│   └── do_i_have_internet.sh
│   └── do_i_have_internet_ping.sh
│   └── do_i_have_internet_osi_model.sh
├── install.sh
└── README.md
```

## Scripts

### `toggle-audio`

Toggles my desktop audio output. So, I have a Fire TV as my secondary monitor that I use as audio. However, I also have a portable AC unit in this room. When the portable AC unit comes on, it can drown out some of the audio that I have on. So, I can then switch to headphones. However, once the temperature in the room has been cooled, the unit cuts itself off. At this point, it is safe to change my audio back to my TV and remove the headphones. Until 5 seconds later when the unit turns back on. I originally coded this to use the sink IDs in this command:

```bash
wpctl status
```

However, I noticed a problem with this. If your computer restarts, it can randomly decide to assign sink IDs to any audio devices it wants. That was inconvenient for my use case. So I used a different strategy in this version, where I looked at the very specific name the device was assigned by PipeWire. As I write this, 52 is the sink ID for my TV, 51 is the sink ID if I wanted all of my audio to come out of my PS5 controller, and 46 would be for my headphones.

![I haven't tried using my PS5 controller as my primary audio source yet. Sorry.](docs/images/example_ps5_speakers.png)

This is likely to change when I restart my computer, which is as infrequently as possible. To handle this, I gave the HEADPHONES and TV variables names and I made the names uppercase because shell convention says “don’t mutate this unless you enjoy pain.” Then, I set a hotkey to ctrl+*, specifically the asterisk on the numpad, because I also use the + and - keys there to change volume. Like, with others keys pressed, not just by themselves like some kind of savage.

Current use case:

- switch between headphones and TV / HDMI audio
- triggered from a GNOME custom keyboard shortcut
- lives at a stable runtime path:

```text
~/.local/bin/toggle-audio
```

The actual source file is:

```text
~/repos/stupid_scripts/bin/toggle-audio
```

### `gnome-status-line`

Generates a compact desktop status line for GNOME / Executor.

The status line is ordered as: CPU, RAM, GPU, VRAM, SSD, controller, phone.

Current idea:

```text
CPU 52° | RAM 20G | GPU 39° | VRAM 6.5G | SSD 1.2T | 🎮95% | 📱95%
```

![the reason the controller is not in this image will be explained later](docs/images/normal_not_eaten_by_angry_lammas.png)

So, I made the switch from Windows 10 to Linux a couple of years ago. When I did, I learned about this really neat and colorful CLI tool called [bpytop](https://github.com/aristocratos/bpytop). These days, use [btop](https://github.com/aristocratos/btop) instead; it is the newer C++ version of the same family and is what I would install now. Getting to the larger overall point, when I used bpytop, I discovered that my processor was trying to catch on fire.

![this should be a picture of my computer on fire](docs/images/bpytop_before.png)

I didn't take pictures of the entire process, but I was able to locate a picture of the CPU cooler that came on my prebuilt CyberPowerPC. If I correctly identified it on the invoice, it was part number FA-106-148, COOLERMASTER I71C CPU AIR COOLER ANODIZED BLACK ALUMINUM + COPPER CORE 120MM ARGB MASTER FAN INTEL, and was listed as an $18 line item expense. Below is the closest picture I was able to find online after Googling the part.

![old cpu cooler](docs/images/old_cpu_cooler.jpg)

So, 4 years after buying the computer, I replaced the CPU cooler with one an acquaintance recommended to me. I didn't realize that I was ordering an engine that mounted on top of a tiny chip, but here we are. It is called the [Dark Rock Pro 5](https://www.bequiet.com/en/cpucooler/4466) if you're interested. I don't know how portable CPU coolers are from machine to machine, but I've been told this one is, so okay. Below is what it looks like in my computer, and a bpytop image of the difference it made:

![rather large cpu cooler. also new](docs/images/new_cpu_cooler.jpg)

![less angry picture of bpytop, it's pretty chill these days](docs/images/bpytop_after.png)

I notice my GPU doesn't use fans very often. It stays pretty chill. I get worried about it, so I included it in my status line.

For questions regarding why VRAM is included, I direct you to my chess related tool: [https://github.com/kain2749/toaster_chess_analysis](https://github.com/kain2749/toaster_chess_analysis) The TLDR is that local LLMs use up a lot of VRAM, and that confused me for about an hour, and since I occasionally still use local LLMs, I decided that should be included.

Well, since now it seems like I was writing a tool to monitor all of the stuff on my computer, I went ahead and added available RAM and amount of storage space remaining. Then I added how much charge is on my phone so I could use the emoji, ... there's also a video game controller emoji! But eventually, you do run out of space for something that's just supposed to give you a glance fast quick system update. 

Anyway, that's the way too long story, below is the stuff an LLM told me to include about the code and what it does. I mean, the code was above the whole time, it's not like this was some recipe blog where I'm keeping an audience captive so you can learn to scramble the perfect egg. You read this because you decided to.

## Temporary NVMe temperature display

`gnome-status-line` currently includes the highest NVMe temperature sensor as `NVMe ##°`.

Reason: Samsung 990 EVO has one warmer internal sensor while running without a heatsink. MC1 Pro heatsink is ordered, oughta be here in about a week. After install and before/after validation, this field will be removed from the top bar.

It is meant to answer the usual “what the hell is my computer doing?” questions at a glance:

- CPU temperature
- available RAM
- GPU temperature
- available VRAM
- free SSD space
- PS5 / DualSense controller battery from UPower
- phone battery from GSConnect

The runtime path is:

```text
~/.local/bin/gnome-status-line
```

The actual source file is:

```text
~/repos/stupid_scripts/bin/gnome-status-line
```

![now with my controller](docs/images/i_decided_to_add_my_controller.png)


## Shell Config

### `shell/bash_aliases`

The Bash aliases that matter most are the Git shortcuts and `batt`, because apparently controller battery telemetry is infrastructure now.

![I could look up what that command does, but I dunno. It gets me the percent charge left in my battery.](docs/images/batt_alias.png)

Backup/source-of-truth for my Bash aliases.

Expected live path:

```text
~/.bash_aliases
```

That should be a symlink to:

```text
~/repos/stupid_scripts/shell/bash_aliases
```

Example aliases:

```bash
alias gs='git status'
alias ga='git add'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline --decorate --graph -20'
alias gd='git diff'
alias gds='git diff --staged'
alias batt='upower -i "$(upower -e | grep -Ei '\''controller'\'' | head -n1)"'
```

### `shell/do_i_have_internet_ping.sh`

I asked ChatGPT for a short script, because I was using my cellphone and wanted something I could run on my desktop. This was the prompt:

```text
What's a short bash script that tries to ping 8.8.8.8 until it works even if it has a failure that causes ping to quit?
```

That is what it spit out. Not quite short, but close enough for government work. Either way, I was interested because it used `#!/usr/bin/env bash` instead of the older `#!/bin/bash` style I am used to seeing.

If you run `env` by itself, it prints the environment variables for your current process environment. Simple enough. If you check the man page, it describes itself as `env - run a program in a modified environment`, which is the more important part here. In a shebang, `#!/usr/bin/env bash` does not mean “use my login shell” or “look at `$SHELL`.” It means “run `/usr/bin/env`, ask it to find `bash` using `$PATH`, and then execute the script with that Bash.” That makes the script more portable across systems where Bash may live at `/bin/bash`, `/usr/bin/bash`, `/usr/local/bin/bash`, or some Homebrew-shaped nonsense.

`env` was not part of 1970s UNIX in the ancient tablet sense. The old machinery was the shell, environment inheritance, `PATH`, and `exec`. `env` came later, in the portability and standardization era, around the POSIX / 4.4BSD neighborhood. So the reason I am used to seeing `#!/bin/bash` instead of `#!/usr/bin/env bash` is probably because I am old enough to have looked at a lot of old-ass scripts. That is not a technical argument. That is just archaeology with back pain.

### `shell/do_i_have_internet.sh`

The actual connectivity check is also worth being specific about. `ping 8.8.8.8` asks a very narrow question: can this machine send an ICMP echo request to `8.8.8.8` and receive an ICMP echo reply? That is a clean test for basic IP reachability, but it is not the same thing as asking whether “the internet works.” It does not test DNS, HTTPS, captive portals, proxies, or whether normal web traffic can get out. It only tests whether ICMP to that specific IP works from here.

A non-ICMP version of that same basic idea is a TCP connect probe. For example, trying to open a TCP connection to `1.1.1.1` or `8.8.8.8` on port `443` asks: can I send a TCP packet out, get packets back, and complete a handshake with a real internet host? That is often closer to what a desktop user actually means by “do I have internet,” because port `443` is normal web traffic and is less likely to be blocked than ICMP. The tradeoff is that it is no longer protocol-neutral. It proves TCP to that host and port works, not that every kind of traffic works.

So the tiny stupid version can use `ping` if all I care about is basic ICMP reachability. If I want something closer to “can this box actually talk to the outside world like a normal computer,” a TCP probe to port `443` is probably the better practical test.

### `shell/do_i_have_internet_osi_model.sh`

Checks whether the machine has internet in a slightly less dumb way than just yelling `ping 8.8.8.8` into the void.

This started as a simple question: “did the wire get connected and can I get a packet out and back?” For that, a single ICMP ping is actually pretty good. It asks a clean, low-level question: can this box send an ICMP echo request to a known external IP and receive the echo reply?

But that is not the same thing as “the internet works.” ICMP can work while DNS is broken. DNS can work while HTTPS is blocked. A TCP connection can work while a captive portal is still doing coffee shop nonsense. So this script checks a few layers and reports which one failed instead of giving one useless yes/no answer.

Current checks:

```text
default route exists
icmp packet out/back
dns resolves name
tcp 443 handshake works
https request works
```

The script runs each check, prints `[ok]` or `[fail]`, then exits with `0` if everything passed or `1` if anything failed.

Example:

```bash
./shell/do_i_have_internet_osi_model.sh
```

Possible output:

```text
[ok]   default route exists
[ok]   icmp packet out/back
[ok]   dns resolves name
[ok]   tcp 443 handshake works
[ok]   https request works
internet: yuh
```

Or, if something is busted:

```text
[ok]   default route exists
[fail] icmp packet out/back
[ok]   dns resolves name
[ok]   tcp 443 handshake works
[ok]   https request works
internet: nu
```

That does not necessarily mean the whole internet is dead. It means one of the assumptions this script cares about failed. Which is the point. A single `ping` gives you one bit of information. This gives you a small failure map.

What the checks mean:

```text
ip route get 1.1.1.1
  The kernel knows where it would send traffic for an outside IP.

ping -q -n -c 1 -W 2 8.8.8.8
  ICMP can leave the machine and come back from a known external IP.

getent hosts example.com
  Name resolution works through the system resolver path, not some random DNS-only tool.

timeout 3 bash -c '</dev/tcp/1.1.1.1/443'
  A TCP handshake to an external HTTPS port works.

curl -fsS --max-time 5 https://example.com
  HTTPS works well enough to make a normal web request.
```

This is not a perfect network diagnostic tool. It is not trying to be. It is a quick sanity check for “is my desktop online in the ways I normally care about?” If this says `internet: yuh`, basic routing, ICMP, DNS, TCP, TLS, and HTTP are all alive enough. If it says `internet: nu`, the failed line tells me where to start swearing.

## Install Script

`install.sh` recreates the local symlink structure.

It should:

- create `~/.local/bin` if missing
- symlink scripts from `bin/` into `~/.local/bin`
- symlink `shell/bash_aliases` into `~/.bash_aliases`
- avoid making `~/bin` a thing again, because no

Run:

```bash
./install.sh
```

## Rules

- Edit scripts in this repo.
- Run scripts from `~/.local/bin`.
- Use symlinks, not hard links.
- Do not put secrets here.
- Do not commit SSH keys, tokens, `.env` files, or anything spicy.
- If a script grows data, generated output, or project state, it probably deserves its own repo.

## Not Here

Bigger projects stay in their own repos.

Example:

```text
~/repos/toaster_chess_analysis
```

This repo can contain convenience wrappers later, but not the whole project state.

## Why

Because rebuilding a Linux desktop from memory is annoying.

Because random scripts become infrastructure when they get hotkeyed.

Because future me will absolutely forget where the working version was.
