![SC2 Banner](resources/SC2_Banner.png)
https://spectrumcollaborationchallenge.com

# Scoring Bot Specification
## Scoring Bot Overview
The Scoring Bot uses the same overall MF-TDMA scheme as used by the Practice Bot. However, instead of using a STATIC or REACTIVE mapping mode, the Scoring bot uses the JERKBOT mapping mode.

As the name implies, this mode can be somewhat more difficult to work with than the Practice Bot.

### JERKBOT Mode
JERKBOT mode results in a default behavior where the bot network randomly select the time-frequency slot allocations. The Scoring Bot will not try to sense or avoid competitor networks in any way.

Additionally, when using the Scoring Bot, the environment simulator will be configured such that competitor transmissions cannot interfere with the Scoring bot. The only way for competitors to influence the behavior of the Scoring bot is via feedback on the Collaboration Channel.


## Scoring Bot Collaboration
The Scoring Bot listens for competitors to send it scalar_performance messages. It will use these scalar_performance messages to determine whether or not its current set of time-frequency slot allocations is harming the competitor network. It will attempt to adapt its use of time frequency slots to minimize the impact on the competitor network.
