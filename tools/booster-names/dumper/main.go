// booster-dumper: reads a Helldivers 2 install (read-only) and writes everything it can find
// about boosters to stdout as JSON, plus strings-en.json (every English text) next to it.
// Built from FileDiver (BSD-3-Clause, xypwn and contributors) by tools/booster-names/build.sh;
// this file is Super Earth Armory Forge's, added to FileDiver's cmd/tools/components/.
//
//	booster-dumper.exe > boosters.json
//
// FileDiver embeds its own copies of the game's data tables and only reads the texts and
// the file index from the install, so this reports what is knowable from files:
//   - enums / types: the library's Booster* enums and types (names where FileDiver knows them)
//   - entities:      every entity that has a Booster component, with its component names
//   - files:         every game file whose (known) name mentions a booster
//   - strings:       every localized text that looks like a booster name or description, in
//     English, Japanese and Chinese, with its string id
//
// HD2_GAME_DIR overrides the install detection (a game on another drive).
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode"

	"github.com/xypwn/filediver/app"
	datalib "github.com/xypwn/filediver/datalibrary"
	"github.com/xypwn/filediver/hashes"
	"github.com/xypwn/filediver/stingray"
	stingray_strings "github.com/xypwn/filediver/stingray/strings"
)

type fileEntry struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type entityEntry struct {
	Name       string         `json:"name"`
	Components []string       `json:"components"`
	Booster    map[string]any `json:"booster_components,omitempty"`
}

type enumEntry struct {
	Value uint64 `json:"value"`
	Name  string `json:"name"`
}

type stringEntry struct {
	ID  uint32 `json:"id"`
	Hex string `json:"hex"`
	En  string `json:"en"`
	Ja  string `json:"ja,omitempty"`
	Zh  string `json:"zh,omitempty"`
}

type output struct {
	About       string         `json:"about"`
	GameDir     string         `json:"game_dir"`
	KnownNames  []string       `json:"known_booster_names"`
	KnownOrder  []string       `json:"known_booster_enum_in_file_order"`
	BoosterEnum []enumEntry    `json:"booster_enum"`
	Phrases     []string       `json:"match_phrases"`
	Enums       map[string]any `json:"enums"`
	Types       map[string]any `json:"types"`
	Entities    []entityEntry  `json:"entities"`
	EntityCount int            `json:"entity_count"`
	Files       []fileEntry    `json:"files"`
	FilesTotal  int            `json:"files_total"`
	FilesNamed  int            `json:"files_with_known_names"`
	Strings     []stringEntry  `json:"strings"`
	StringCount map[string]int `json:"string_counts"`
}

// the library has no strings: a value is "Booster_362a" (its offset) unless FileDiver knows the name
var placeholder = regexp.MustCompile(`^[0-9a-f]+$`)

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}

func hasBooster(s string) bool { return strings.Contains(strings.ToLower(s), "booster") }

// "UAVRecon" -> "UAV Recon", "HellpodSpaceOptimization" -> "Hellpod Space Optimization"
func camelSplit(s string) string {
	r := []rune(s)
	var out []rune
	for i, c := range r {
		if i > 0 && unicode.IsUpper(c) {
			prev := r[i-1]
			nextLower := i+1 < len(r) && unicode.IsLower(r[i+1])
			if unicode.IsLower(prev) || unicode.IsDigit(prev) || (unicode.IsUpper(prev) && nextLower) {
				out = append(out, ' ')
			}
		}
		out = append(out, c)
	}
	return string(out)
}

func main() {
	ctx := context.Background()

	gameDir := os.Getenv("HD2_GAME_DIR")
	if gameDir == "" {
		d, err := app.DetectGameDir()
		if err != nil {
			fatal("Unable to detect game install directory (%v). Drag the Helldivers 2 folder onto Run-me.bat.", err)
		}
		gameDir = d
	}

	known := hashes.ParseHashes(hashes.Hashes)
	hashesMap := make(map[stingray.Hash]string, len(known))
	for _, n := range known {
		hashesMap[stingray.Sum(n)] = n
	}
	dlNames := hashes.ParseHashes(hashes.DLTypeNames)
	dlMap := make(map[datalib.DLHash]string, len(dlNames))
	for _, n := range dlNames {
		dlMap[datalib.Sum(n)] = n
	}
	dlName := func(h datalib.DLHash) string {
		if n, ok := dlMap[h]; ok {
			return n
		}
		return h.String()
	}
	lookupHash := func(h stingray.Hash) string {
		if n, ok := hashesMap[h]; ok {
			return n
		}
		return h.String()
	}

	dataDir, err := stingray.OpenDataDir(ctx, filepath.Join(gameDir, "data"), func(curr, total int) {
		fmt.Fprintf(os.Stderr, "\rReading the game index %3.0f%%", float64(curr)/float64(total)*100)
	})
	fmt.Fprintln(os.Stderr)
	if err != nil {
		fatal("Could not open the game data (%v). Is this the Helldivers 2 folder, the one holding \"data\"?", err)
	}

	out := output{
		About:   "Super Earth Armory Forge booster dump. Send this file and strings-en.json to the mod author.",
		GameDir: gameDir, Enums: map[string]any{}, Types: map[string]any{}, StringCount: map[string]int{},
		Entities: []entityEntry{}, Files: []fileEntry{}, Strings: []stringEntry{},
	}

	// names FileDiver knows
	var boosterEnumValues []string
	for _, n := range dlNames {
		if hasBooster(n) {
			out.KnownNames = append(out.KnownNames, n)
			if strings.HasPrefix(n, "Booster_") {
				boosterEnumValues = append(boosterEnumValues, strings.TrimPrefix(n, "Booster_"))
				out.KnownOrder = append(out.KnownOrder, n)
			}
		}
	}
	sort.Strings(out.KnownNames)

	// the type library: enums and types that mention boosters
	if tl, err := datalib.ParseTypeLib(nil); err == nil {
		for h, e := range tl.Enums {
			name := e.Name
			if name == "" {
				name = dlName(h)
			}
			if hasBooster(name) {
				out.Enums[name] = e
				for _, v := range e.Values {
					if name == "Booster" {
						out.BoosterEnum = append(out.BoosterEnum, enumEntry{Value: v.Value, Name: v.Name})
					}
					if rest, ok := strings.CutPrefix(v.Name, "Booster_"); ok && !placeholder.MatchString(rest) {
						boosterEnumValues = append(boosterEnumValues, rest)
					}
				}
			}
		}
		for h, t := range tl.Types {
			name := t.Name
			if name == "" {
				name = dlName(h)
			}
			if hasBooster(name) {
				out.Types[name] = t
			}
		}
	} else {
		fmt.Fprintf(os.Stderr, "type library: %v\n", err)
	}

	sort.Slice(out.BoosterEnum, func(i, j int) bool { return out.BoosterEnum[i].Value < out.BoosterEnum[j].Value })

	// entities with a Booster component
	if ents, err := datalib.ParseEntityComponentSettings(); err == nil {
		out.EntityCount = len(ents)
		for res, e := range ents {
			var comps []string
			found := false
			for ch := range e.Components {
				n := dlName(ch)
				comps = append(comps, n)
				if hasBooster(n) {
					found = true
				}
			}
			if !found {
				continue
			}
			sort.Strings(comps)
			ee := entityEntry{Name: lookupHash(res), Components: comps, Booster: map[string]any{}}
			for ch, c := range e.Components {
				if n := dlName(ch); hasBooster(n) {
					ee.Booster[n] = c.ToSimple(lookupHash, func(t stingray.ThinHash) string { return t.String() }, func(id uint32) string { return fmt.Sprint(id) })
				}
			}
			out.Entities = append(out.Entities, ee)
		}
		sort.Slice(out.Entities, func(i, j int) bool { return out.Entities[i].Name < out.Entities[j].Name })
	} else {
		fmt.Fprintf(os.Stderr, "entities: %v\n", err)
	}

	// game files whose name mentions a booster
	out.FilesTotal = len(dataDir.Files)
	for id := range dataDir.Files {
		n, ok := hashesMap[id.Name]
		if ok {
			out.FilesNamed++
		}
		if ok && hasBooster(n) {
			out.Files = append(out.Files, fileEntry{Name: n, Type: lookupHash(id.Type)})
		}
	}
	sort.Slice(out.Files, func(i, j int) bool {
		if out.Files[i].Name != out.Files[j].Name {
			return out.Files[i].Name < out.Files[j].Name
		}
		return out.Files[i].Type < out.Files[j].Type
	})

	// texts: English picks them, Japanese and Chinese are looked up by the same id
	langs := map[string]map[uint32]string{}
	for key, friendly := range map[string]string{"en": "English (US)", "ja": "Japanese", "zh": "Chinese (Simplified)"} {
		if h, ok := stingray_strings.LanguageFriendlyNameToHash[friendly]; ok {
			langs[key] = stingray_strings.LoadLanguageMap(dataDir, h)
			out.StringCount[key] = len(langs[key])
		}
	}
	en := langs["en"]
	phraseSet := map[string]bool{}
	var single []string
	for _, v := range boosterEnumValues {
		p := camelSplit(v)
		if strings.Contains(p, " ") {
			phraseSet[strings.ToLower(p)] = true
		} else if len(p) > 3 {
			single = append(single, strings.ToLower(p))
		}
	}
	for p := range phraseSet {
		out.Phrases = append(out.Phrases, p)
	}
	sort.Strings(out.Phrases)
	out.Phrases = append(out.Phrases, "booster")
	for id, t := range en {
		low := strings.ToLower(strings.TrimSpace(t))
		match := strings.Contains(low, "booster")
		for p := range phraseSet {
			if match {
				break
			}
			match = strings.Contains(low, p)
		}
		for _, s := range single {
			if match {
				break
			}
			match = low == s
		}
		if match {
			out.Strings = append(out.Strings, stringEntry{ID: id, Hex: fmt.Sprintf("0x%08x", id), En: t, Ja: langs["ja"][id], Zh: langs["zh"][id]})
		}
	}
	sort.Slice(out.Strings, func(i, j int) bool { return out.Strings[i].ID < out.Strings[j].ID })

	// every English text, for matching offline
	all := make(map[string]string, len(en))
	for id, t := range en {
		all[fmt.Sprint(id)] = t
	}
	if b, err := json.Marshal(all); err == nil {
		if err := os.WriteFile("strings-en.json", b, 0o644); err != nil {
			fmt.Fprintf(os.Stderr, "strings-en.json: %v\n", err)
		}
	}

	b, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		fatal("%v", err)
	}
	fmt.Println(string(b))
}
