# This project is likely PERMANENTLY on hold due to making a GNOME status bar. I no longer see the need to create a KDE widget. I am keeping the notes I made for this project in case if I change my mind for some reason

# KDE Plasma Test Lab Notes

Goal: test KDE Plasma as a script/widget dashboard environment without contaminating the main GNOME setup more than necessary.

## Current decision

Do **not** migrate desktop environments yet.

Current Pop!_OS / GNOME setup is working:

- Normal OS updates handled Copy Fail / Dirty Frag mitigation.
- Running kernel matched installed kernel.
- No reboot-required flag.
- Vulnerable/related modules were not loaded:
  - `rxrpc`
  - `esp4`
  - `esp6`
  - `algif_aead`
- GNOME workflow is already functional:
  - phone battery notifications
  - audio output hotkey toggle between Fire TV and headphones
  - Steam / recording / browser workflow
  - dock / floating desktop layout

KDE is interesting mainly because it may make script state more visible and embedded in the desktop.

## Why KDE is worth testing

KDE Plasma is a better fit for persistent desktop-script state, such as a tiny panel/widget showing:

```text
🎮 87% | 📱 42% | 🔊 TV
```

Possible widget actions:

- click: switch audio output
- middle-click: refresh battery state
- right-click: open config/logs

This is more useful than generic desktop “ricing.” It would turn the DE into a small operational dashboard for existing shell scripts.

## Keep GNOME as the stable daily driver

Current GNOME script setup is already “embedded enough” because hotkeys work.

Example current workflow:

```text
press key
audio swaps
notification confirms output
go back to game/work
```

That is not broken. It is just slightly ugly.

Do not migrate just because KDE is theoretically cleaner.

Only consider KDE seriously if it solves a real problem:

- better persistent panel widgets
- better window placement rules
- better OBS/game/browser layout automation
- better visibility into controller/phone/audio state
- less extension pain than GNOME

## Safer KDE test approach: disposable user

Create a separate test user so KDE can write configs into that user's home directory instead of the main `kain` GNOME profile.

```bash
sudo adduser kdetest
sudo usermod -aG sudo kdetest
```

Install KDE Plasma lightly:

```bash
sudo apt update
sudo apt install kde-plasma-desktop
```

Log out, select Plasma on the login screen, and log in as `kdetest`.

KDE can then dump config into:

```text
/home/kdetest/.config
/home/kdetest/.local
/home/kdetest/.cache
```

The main GNOME user remains cleaner.

## Copy scripts from main user while testing

From the `kdetest` account, copy needed scripts from `/home/kain` with sudo:

```bash
sudo cp /home/kain/path/to/script.sh /home/kdetest/
sudo chown kdetest:kdetest /home/kdetest/script.sh
```

Alternative: use a neutral shared lab path:

```bash
sudo mkdir -p /opt/kde-lab
sudo chown -R kain:kain /opt/kde-lab
```

A git repo can live there, or inside `/home/kdetest`, depending on what is less annoying.

## Package install logging

Before installing KDE, snapshot package state:

```bash
mkdir -p ~/kde-test-log
apt-mark showmanual | sort > ~/kde-test-log/manual-before.txt
dpkg-query -W -f='${binary:Package}\n' | sort > ~/kde-test-log/packages-before.txt
```

Simulate the KDE install first:

```bash
sudo apt install -s kde-plasma-desktop | tee ~/kde-test-log/kde-install-sim.txt
```

If the simulated install looks acceptable, install for real and log output:

```bash
sudo apt install kde-plasma-desktop 2>&1 | tee ~/kde-test-log/kde-install-real.txt
```

After installation:

```bash
apt-mark showmanual | sort > ~/kde-test-log/manual-after.txt
dpkg-query -W -f='${binary:Package}\n' | sort > ~/kde-test-log/packages-after.txt

comm -13 ~/kde-test-log/manual-before.txt ~/kde-test-log/manual-after.txt > ~/kde-test-log/manual-added.txt
comm -13 ~/kde-test-log/packages-before.txt ~/kde-test-log/packages-after.txt > ~/kde-test-log/packages-added.txt
```

Useful logs:

```text
~/kde-test-log/kde-install-real.txt
~/kde-test-log/manual-added.txt
~/kde-test-log/packages-added.txt
```

## Rollback plan

After scripts/widgets are committed and pushed to git, remove the KDE test user:

```bash
sudo deluser --remove-home kdetest
```

Remove KDE package:

```bash
sudo apt purge kde-plasma-desktop
sudo apt autoremove --purge
```

If using the package-state diff, inspect before purging anything from `manual-added.txt`:

```bash
less ~/kde-test-log/manual-added.txt
```

Possible purge using the manual-added list:

```bash
sudo apt purge $(cat ~/kde-test-log/manual-added.txt)
sudo apt autoremove --purge
```

Do **not** blindly run that if other packages were installed after the KDE test and should be kept.

## Main-user KDE config cleanup

If KDE was accidentally launched under the main `kain` user, do not immediately shotgun-delete configs. Quarantine first:

```bash
mkdir -p ~/kde-config-backup
mv ~/.config/plasma* ~/.config/kde* ~/.config/kwin* ~/kde-config-backup/ 2>/dev/null
mv ~/.local/share/plasma* ~/.local/share/kxmlgui5 ~/kde-config-backup/ 2>/dev/null
mv ~/.cache/plasma* ~/kde-config-backup/ 2>/dev/null
```

Then log out/in and verify GNOME still behaves normally.

## Suggested repo shape

```text
desktop-dashboard-lab/
  README.md
  scripts/
    audio-toggle.sh
    ps5-battery.sh
    phone-battery.sh
  plasmoid/
    ...
  notes/
    kde-plasma-test-log.md
  screenshots/
```

Avoid versioning the entire `~/.config`. Keep the repo limited to scripts, widget source, notes, screenshots, and reproducible setup steps.

## Test objective

Do **not** test “switching to KDE.”

Test one focused question:

> Can KDE Plasma provide a small panel widget/dashboard for PS5 controller battery, phone battery, and audio output state without becoming a pain in the ass?

If yes, KDE becomes a serious candidate.

If no, GNOME stays the daily driver and the experiment still produced useful scripts/notes.

## Current practical verdict

Pop!_OS / GNOME is winning by being boring and functional.

KDE Plasma is worth a controlled lab test later, especially for persistent desktop widgets, but not worth disrupting the working desktop right now.
