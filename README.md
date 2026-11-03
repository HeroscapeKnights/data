# Heroscape Knights data

Reviewed data for every official Heroscape army card, from Hasbro and Wizards of the Coast (2004-2011) to Renegade Game Studios (2024 onward): stats, abilities, current points under each point system, card and figure images, and the sets they came in. [Heroscape Knights](https://heroscapeknights.pages.dev) is built from the same data.

The tables in `tables/` are TSV files you can read here on GitHub. The same data is served as JSON at <https://api.heroscapeknights.com>.

## The API

```
https://api.heroscapeknights.com/index.json               every version, newest first, and which is latest
https://api.heroscapeknights.com/latest/units.json        the current data
https://api.heroscapeknights.com/2026-11-04/units.json    a dated version, which never changes
```

Each version has these files:

| File | What's in it |
|---|---|
| `units.json` | Every unit: stats, abilities, `points` under each system (a missing system means unpriced), and `images` (card fronts and figure photos, each with its `credit`) |
| `sets.json` | Card sets and waves, with release dates |
| `point_systems.json` | Each point system and the release its points come from |
| `all.json` | All three in one file |
| `index.json` | The version, the date the data was read, the files and their counts |

`latest/` always matches the tables in this repository. Each change to the tables publishes a new version named for its day. A second change on the same day gets a suffix, such as `2026-11-04.2`. Pin a dated version if you don't want the data to change under you.

```bash
curl -s https://api.heroscapeknights.com/latest/units.json | jq '.[] | select(.general == "Jandar") | .display_name'
curl -s https://api.heroscapeknights.com/latest/units.json | jq '.[] | select(.id == "zelrig") | .points'
```

```js
const units = await (await fetch("https://api.heroscapeknights.com/latest/units.json")).json();
```

Dates are partial ISO dates (`YYYY`, `YYYY-MM` or `YYYY-MM-DD`). An unknown value is `null`, and list fields are always present, possibly empty. A unit's `type` combines `rarity` and `kind`, such as `unique-hero`. `hexes` is the total number of spaces for all of a card's figures.

**Images are hotlinked from their owners, never copied here.** Show each image's `credit` wherever you show the image.

## The tables

```
tables/units.tsv            one row per army card
tables/abilities.tsv        special powers, in card order
tables/images.tsv           card and figure images, with credits
tables/sets.tsv             card sets and waves
tables/point_systems.tsv    point systems and the release each uses
tables/point_releases.tsv   those releases
tables/points/<system>/<release>.tsv   points for each unit
datapackage.json            column types and keys for every table
```

The format is TSV, UTF-8, with one header row. An empty cell means null, and list columns join items with `;`. Inside a cell, `\n` is a line break, `\t` a tab and `\\` a backslash. A cell containing a double quote is wrapped in double quotes, with the quotes inside doubled. Ids are lowercase slugs and never change.

The tables are maintained in another repository, where each change is checked against the official cards before it's published here. Corrections are welcome as issues.

`scripts/build_api.py` builds the JSON from the tables using only Python's standard library: `python3 scripts/build_api.py --check`.

## Sources

Card text, stats, official points and card images come from Renegade Game Studios' [card database](https://playheroscape.renegadegamestudios.com/cards). Delta points come from the Delta committee on [heroscapers.com](https://www.heroscapers.com/threads/delta-latest-updates-and-discussion.59583/), as tracked by [heroscape.org](https://heroscape.org/builder/). Release data comes from heroscape.org, the [Heroscape Wiki](https://heroscape.fandom.com) and glasq.com. Figure photos belong to the retailers and photographers named in each image's credit.

HEROSCAPE is a trademark of Hasbro, used under license by Renegade Game Studios. Marvel, Dungeons & Dragons and G.I. Joe are trademarks of their owners. This is a fan project, not affiliated with any of them.
