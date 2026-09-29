# From a football results API to a half-time/full-time heatmap in R
# Data: Football Charts API (free for the current and previous season, no key
# needed). Attribution: "Data by football-charts.com".
# Tutorial: https://www.football-charts.com/insights/ht-ft-heatmap-r

library(jsonlite)
library(dplyr)
library(tidyr)
library(ggplot2)

# 1. Load ---------------------------------------------------------------
# One request returns every finished match of a league-season.
url <- "https://footballcharts-backend.onrender.com/api/v1/leagues/germany3/results/?season=2025-2026"
resp <- fromJSON(url)
matches <- as_tibble(resp$matches)
cat(nrow(matches), "matches;", resp$attribution, "\n")

# 2. Parse the "home:away" score strings ----------------------------------
split_score <- function(x) {
  parts <- strsplit(x, ":", fixed = TRUE)
  list(home = as.integer(vapply(parts, function(p) p[1], "")),
       away = as.integer(vapply(parts, function(p) p[2], "")))
}
ft <- split_score(matches$score)
ht <- split_score(matches$ht_result)

games <- matches |>
  transmute(date = as.Date(date),
            home = homeTeam, away = awayTeam,
            ft_home = ft$home, ft_away = ft$away,
            ht_home = ht$home, ht_away = ht$away)

# 3. Check before counting -------------------------------------------------
stopifnot(
  nrow(games) == 380,                                        # 20 teams, 38 rounds
  !anyNA(games[, c("ft_home", "ft_away", "ht_home", "ht_away")]),
  !any(duplicated(games[, c("date", "home", "away")])),
  all(games$ht_home <= games$ft_home), all(games$ht_away <= games$ft_away)
)
per_team <- table(c(games$home, games$away))
stopifnot(length(per_team) == 20, all(per_team == 38))
cat("checks passed: 20 teams x 38 matches, no missing or impossible scores\n")

# 4. Half-time state -> full-time result -----------------------------------
state <- function(h, a) factor(sign(h - a), levels = c(1, 0, -1),
                               labels = c("Home leads", "Level", "Away leads"))
result <- function(h, a) factor(sign(h - a), levels = c(1, 0, -1),
                                labels = c("Home win", "Draw", "Away win"))

htft <- games |>
  mutate(ht = state(ht_home, ht_away), ft = result(ft_home, ft_away)) |>
  count(ht, ft, .drop = FALSE) |>
  group_by(ht) |>
  mutate(row_total = sum(n), pct = 100 * n / row_total) |>   # share WITHIN each half-time state
  ungroup()

print(htft, n = 9)

# 5. Heatmap ---------------------------------------------------------------
p <- ggplot(htft, aes(ft, ht, fill = pct)) +
  geom_tile(colour = "white", linewidth = 1) +
  geom_text(aes(label = sprintf("%.0f%%\n(%d)", pct, n)), size = 4.2) +
  scale_fill_gradient(low = "#eef2ff", high = "#1e40af", limits = c(0, 100), guide = "none") +
  scale_y_discrete(limits = rev) +
  labs(title = "3. Liga 2025-26: what happened after half-time",
       subtitle = "Row % = share of full-time results for each half-time state (n = 380)",
       x = "Full-time result", y = "At half-time",
       caption = "Data by football-charts.com") +
  theme_minimal(base_size = 12) +
  theme(panel.grid = element_blank())

ggsave("ht_ft_heatmap_3liga_2025-26.png", p, width = 7, height = 4.6, dpi = 150, bg = "white")
cat("saved ht_ft_heatmap_3liga_2025-26.png\n")
