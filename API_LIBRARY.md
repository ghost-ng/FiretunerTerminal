# Civ 7 JavaScript API Library

A community-built quick reference for the Civilization 7 debug console JavaScript API. This API is accessed through the FireTuner debug port (TCP 4318). The methods and objects are visible in the game's JS files, but digging through them every time is slow — this library consolidates what's known into a single searchable reference to speed up troubleshooting and modding.

> **This is a living document.** If you discover new API calls, useful patterns, or corrections, please [open a pull request](https://github.com/ghost-ng/FiretunerTerminal/pulls) to add them. The more people contribute, the more useful this becomes for everyone.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Tips for AI Agents](#tips-for-ai-agents)
- [Global Objects](#global-objects)
- [GameplayMap](#gameplaymap)
- [Players](#players)
- [Player Instance](#player-instance)
- [Player.Cities](#playercities)
- [City Instance](#city-instance)
- [Player.Units](#playerunits)
- [Unit Instance](#unit-instance)
- [Player.Techs](#playertechs)
- [Player.Culture](#playerculture)
- [Player.Treasury](#playertreasury)
- [Player.Diplomacy](#playerdiplomacy)
- [Player.Resources](#playerresources)
- [Player.Trade](#playertrade)
- [Game](#game)
- [Game.Diplomacy](#gamediplomacy)
- [Game.VictoryManager](#gamevictorymanager)
- [Game.Religion](#gamereligion)
- [Game.Combat](#gamecombat)
- [Game.Trade](#gametrade)
- [Game.CityStates](#gamecitystates)
- [GameContext](#gamecontext)
- [Configuration](#configuration)
- [UI](#ui)
- [WorldBuilder](#worldbuilder)
- [Useful Patterns](#useful-patterns)
- [Contributing](#contributing)

---

## Quick Start

Every example below is a JavaScript expression you can send via `execute_js()` (MCP) or type directly into the FireTuner Terminal.

```js
// Simple expression - returns "2"
1 + 1

// Get map size
GameplayMap.getGridWidth() + "x" + GameplayMap.getGridHeight()

// Get all player data as JSON
JSON.stringify(Players.getAliveMajorIds(), null, 2)
```

**Key rule:** The last expression in your code is the return value. Use `JSON.stringify()` for complex objects — raw objects often return `[object Object]`.

## Tips for AI Agents

When using the MCP server's `execute_js` tool:

1. **Always use `JSON.stringify()`** for structured data — the debug port returns the string representation of the last expression
2. **Multiline scripts work** — send full code blocks, the last expression is returned
3. **Error messages are returned as strings** — look for `TypeError:`, `ReferenceError:`, etc. in responses
4. **Localization keys** — Many names return `LOC_` prefixed keys (e.g., `LOC_CIVILIZATION_EGYPT_FULLNAME`) rather than display names
5. **Probe unknown objects** — Use `Object.getOwnPropertyNames(obj)` and `Object.getOwnPropertyNames(Object.getPrototypeOf(obj))` to discover available properties and methods
6. **Check `typeof`** before calling — `typeof SomeGlobal` returns `"undefined"` if it doesn't exist

---

## Global Objects

| Object | Type | Description |
|--------|------|-------------|
| `GameplayMap` | object | Map data — terrain, features, continents, yields |
| `Players` | object | Player collection — lookup, iteration, alive checks |
| `Game` | object | Game systems — diplomacy, religion, combat, victory |
| `GameContext` | object | Turn management — send turn complete, pause, retire |
| `Configuration` | object | Game/map/player configuration settings |
| `UI` | object | UI system — icons, cursors, audio, options |
| `WorldBuilder` | object | World builder tools (limited: `startBlock`, `endBlock`) |

---

## GameplayMap

Map data and tile queries. All tile functions take `(x, y)` coordinates.

### Map Info
| Method | Returns | Description |
|--------|---------|-------------|
| `getGridWidth()` | `number` | Map width in tiles |
| `getGridHeight()` | `number` | Map height in tiles |
| `getMapSize()` | `number` | Map size enum |
| `getPlotCount()` | `number` | Total number of plots |
| `getRandomSeed()` | `number` | Map generation seed |
| `getPrimaryHemisphere()` | `number` | Primary hemisphere |

### Tile Properties
| Method | Returns | Description |
|--------|---------|-------------|
| `getTerrainType(x, y)` | `number` | Terrain type at tile |
| `getBiomeType(x, y)` | `number` | Biome type at tile |
| `getFeatureType(x, y)` | `number` | Feature type (forest, jungle, etc.) |
| `getFeatureClassType(x, y)` | `number` | Feature class type |
| `getResourceType(x, y)` | `number` | Resource type at tile |
| `getElevation(x, y)` | `number` | Tile elevation |
| `getRainfall(x, y)` | `number` | Tile rainfall |
| `getFertilityType(x, y)` | `number` | Fertility type |
| `getAppeal(x, y)` | `number` | Tile appeal value |
| `getContinentType(x, y)` | `number` | Continent ID (-1 if none) |
| `getRegionId(x, y)` | `number` | Region ID |
| `getAreaId(x, y)` | `number` | Area ID |
| `getLandmassId(x, y)` | `number` | Landmass ID |
| `getLandmassRegionId(x, y)` | `number` | Landmass region ID |
| `getOwner(x, y)` | `number` | Owning player ID |
| `getOwnerName(x, y)` | `string` | Owning player name |
| `getOwnerHostility(x, y)` | `number` | Hostility level of owner |
| `getOwningCityFromXY(x, y)` | `object` | City that owns this tile |
| `getRouteType(x, y)` | `number` | Route/road type |
| `getRouteAgeType(x, y)` | `number` | Route age type |

### Yields
| Method | Returns | Description |
|--------|---------|-------------|
| `getYield(x, y, yieldType)` | `number` | Specific yield value |
| `getYields(x, y)` | `object` | All yields for tile |
| `getYieldWithCity(x, y, yieldType)` | `number` | Yield including city bonuses |
| `getYieldsWithCity(x, y)` | `object` | All yields including city bonuses |

### Tile Checks
| Method | Returns | Description |
|--------|---------|-------------|
| `isWater(x, y)` | `boolean` | Is water tile |
| `isLake(x, y)` | `boolean` | Is lake |
| `isMountain(x, y)` | `boolean` | Is mountain |
| `isImpassable(x, y)` | `boolean` | Is impassable |
| `isCoastalLand(x, y)` | `boolean` | Is coastal land |
| `isFreshWater(x, y)` | `boolean` | Has fresh water |
| `isRiver(x, y)` | `boolean` | Has river |
| `isNavigableRiver(x, y)` | `boolean` | Has navigable river |
| `isNaturalWonder(x, y)` | `boolean` | Is natural wonder |
| `isVolcano(x, y)` | `boolean` | Is volcano |
| `isVolcanoActive(x, y)` | `boolean` | Is active volcano |
| `isFerry(x, y)` | `boolean` | Has ferry |
| `isCliffCrossing(x, y, direction)` | `boolean` | Cliff crossing check |
| `isAdjacentToLand(x, y)` | `boolean` | Adjacent to land |
| `isAdjacentToRivers(x, y)` | `boolean` | Adjacent to river |
| `isAdjacentToShallowWater(x, y)` | `boolean` | Adjacent to shallow water |
| `isAdjacentToFeature(x, y, featureType)` | `boolean` | Adjacent to feature |
| `isAdjacentToAnotherBiome(x, y)` | `boolean` | Adjacent to different biome |
| `getAreaIsWater(areaId)` | `boolean` | Is area water |

### Spatial Queries
| Method | Returns | Description |
|--------|---------|-------------|
| `getPlotDistance(x1, y1, x2, y2)` | `number` | Distance between tiles |
| `getPlotIndicesInRadius(x, y, radius)` | `array` | Plot indices within radius |
| `getAdjacentPlotLocation(x, y, direction)` | `object` | Adjacent tile location |
| `getDirectionToPlot(x1, y1, x2, y2)` | `number` | Direction from one tile to another |
| `getHemisphere(x, y)` | `number` | Hemisphere of tile |
| `getPlotLatitude(x, y)` | `number` | Latitude of tile |
| `findSecondContinent(x, y)` | `number` | Find second continent from tile |

### Index/Location Conversion
| Method | Returns | Description |
|--------|---------|-------------|
| `getIndexFromLocation(location)` | `number` | Plot index from location object |
| `getIndexFromXY(x, y)` | `number` | Plot index from coordinates |
| `getLocationFromIndex(index)` | `object` | Location `{x, y}` from index |
| `isValidLocation(location)` | `boolean` | Check if location is valid |
| `isValidXY(x, y)` | `boolean` | Check if coordinates are valid |
| `isValidIndex(index)` | `boolean` | Check if index is valid |

### Other
| Method | Returns | Description |
|--------|---------|-------------|
| `getRiverName(x, y)` | `string` | Name of river |
| `getVolcanoName(x, y)` | `string` | Name of volcano |
| `getRevealedState(x, y, player)` | `number` | Fog of war state for player |
| `getRevealedStates(x, y)` | `object` | All revealed states |
| `getPlotTag(x, y, tag)` | `boolean` | Check plot tag |
| `hasPlotTag(x, y, tag)` | `boolean` | Has plot tag |
| `getProperty(x, y, property)` | `any` | Get plot property |
| `isCityWithinMinimumDistance(x, y)` | `boolean` | City settle distance check |
| `isPlotInAdvancedStartRegion(x, y, player)` | `boolean` | Advanced start region check |

---

## Players

Player collection and lookup.

| Method | Returns | Description |
|--------|---------|-------------|
| `get(playerId)` | `Player` | Get player by ID |
| `getAlive()` | `array` | All alive player IDs |
| `getAliveIds()` | `array` | All alive player IDs |
| `getAliveMajorIds()` | `array` | Alive major civ IDs |
| `getAliveMinorIds()` | `array` | Alive minor civ IDs |
| `getAliveBarbarianIds()` | `array` | Alive barbarian IDs |
| `getAliveIndependentIds()` | `array` | Alive independent IDs |
| `getEverAlive()` | `array` | All ever-alive player IDs |
| `getWasEverAliveIds()` | `array` | Was-ever-alive IDs |
| `getWasEverAliveMajorIds()` | `array` | Was-ever-alive major IDs |
| `getWasEverAliveMinorIds()` | `array` | Was-ever-alive minor IDs |
| `getNumWasEverAliveMajors()` | `number` | Count of ever-alive majors |
| `isAlive(playerId)` | `boolean` | Is player alive |
| `wasEverAlive(playerId)` | `boolean` | Was player ever alive |
| `isValid(playerId)` | `boolean` | Is valid player ID |
| `isAI(playerId)` | `boolean` | Is AI player |
| `isHuman(playerId)` | `boolean` | Is human player |
| `isObserver(playerId)` | `boolean` | Is observer |
| `isParticipant(playerId)` | `boolean` | Is participant |
| `getFavoredWonders()` | `object` | Favored wonders |
| `grantGreatWork(playerId, ...)` | | Grant great work |
| `grantYield(playerId, ...)` | | Grant yield to player |

---

## Player Instance

Properties and sub-objects of `Players.get(id)`.

### Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | `number` | Player ID |
| `name` | `string` | Player name |
| `leaderName` | `string` | Leader name (localization key) |
| `leaderType` | `string` | Leader type identifier |
| `civilizationName` | `string` | Civilization short name |
| `civilizationFullName` | `string` | Civilization full name (localization key) |
| `civilizationAdjective` | `string` | Civilization adjective |
| `civilizationType` | `string` | Civilization type identifier |
| `team` | `number` | Team ID |
| `level` | `number` | Difficulty level |
| `controlType` | `number` | Control type |
| `isAlive` | `boolean` | Is alive |
| `isHuman` | `boolean` | Is human-controlled |
| `isAI` | `boolean` | Is AI-controlled |
| `isMajor` | `boolean` | Is major civilization |
| `isMinor` | `boolean` | Is minor civilization |
| `isBarbarian` | `boolean` | Is barbarian |
| `isIndependent` | `boolean` | Is independent |
| `isValid` | `boolean` | Is valid |
| `isTurnActive` | `boolean` | Is turn active |
| `wasEverAlive` | `boolean` | Was ever alive |
| `canUnreadyTurn` | `boolean` | Can unready turn |

### Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `isDistantLands(location)` | `boolean` | Is location on distant lands for this player |
| `getProperty(name)` | `any` | Get player property by name |

### Sub-Objects
| Property | Description |
|----------|-------------|
| `Cities` | City management |
| `Units` | Unit management |
| `Techs` | Technology tree |
| `Culture` | Civics / culture tree |
| `Treasury` | Gold / finances |
| `Diplomacy` | Diplomatic relations |
| `Resources` | Resource management |
| `Trade` | Trade routes |
| `Districts` | District management |
| `Improvements` | Improvements |
| `Religion` | Religious beliefs |
| `Happiness` | Happiness system |
| `Visibility` | Map visibility |
| `AI` | AI controller |
| `Armies` | Army management |
| `Formations` | Formation management |
| `Constructibles` | Constructible items |
| `GreatPeoplePoints` | Great people points |
| `Espionage` | Espionage system |
| `Influence` | Influence system |
| `Legacies` | Legacy system |
| `LegacyPaths` | Legacy paths |
| `Ages` | Age progression |
| `Victories` | Victory progress |
| `Scoring` | Score tracking |
| `Stats` | Statistics |
| `Workers` | Worker management |
| `WMDs` | Weapons of mass destruction |
| `Modifiers` | Active modifiers |
| `TurnManager` | Turn management |
| `Identity` | Identity system |
| `AdvancedStart` | Advanced start |
| `Advisory` | Advisor system |
| `GoodyHut` | Goody hut tracking |
| `Quests` | Quest system |
| `Stories` | Narrative stories |
| `NameManager` | Name management |

---

## Player.Cities

`Players.get(id).Cities` — City collection for a player.

| Method | Returns | Description |
|--------|---------|-------------|
| `getCities()` | `array<City>` | All cities as array |
| `getCityIds()` | `array<{owner, id, type}>` | City ID objects |
| `getCapital()` | `City` | Capital city |
| `findClosest(x, y)` | `City` | Nearest city to location |
| `destroy(cityId)` | | Destroy a city |

---

## City Instance

Properties and sub-objects of a city.

### Properties
| Property | Type | Description |
|----------|------|-------------|
| `name` | `string` | City name (localization key) |
| `id` | `object` | City ID `{owner, id, type}` |
| `localId` | `number` | Local city ID |
| `location` | `{x, y}` | City tile coordinates |
| `owner` | `number` | Owner player ID |
| `originalOwner` | `number` | Original owner player ID |
| `population` | `number` | Total population |
| `urbanPopulation` | `number` | Urban population |
| `ruralPopulation` | `number` | Rural population |
| `pendingPopulation` | `number` | Pending population |
| `isCapital` | `boolean` | Is capital city |
| `isTown` | `boolean` | Is town (not full city) |
| `isBeingRazed` | `boolean` | Being razed |
| `isInfected` | `boolean` | Is infected |
| `isValid` | `boolean` | Is valid |
| `isDistantLands` | `boolean` | On distant lands |

### Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `getTurnsUntilRazed` | `number` | Turns until razed (property, not method) |
| `isJustConqueredFrom(playerId)` | `boolean` | Was just conquered from player |
| `getProperty(name)` | `any` | Get city property |
| `getConnectedCities()` | `array` | Connected cities |
| `getPurchasedPlots()` | `array` | Purchased plot list |
| `getSentFoodPerCity()` | `number` | Food sent per city |
| `purchasePlot(x, y)` | | Purchase a plot |
| `addRuralPopulation(amount)` | | Add rural population |

### Sub-Objects
| Property | Description |
|----------|-------------|
| `Growth` | Population growth |
| `Production` | Production queue |
| `Yields` | City yields |
| `Districts` | City districts |
| `BuildQueue` | Build queue |
| `FoodQueue` | Food queue |
| `Trade` | City trade |
| `Gold` | City gold |
| `Culture` | City culture |
| `Religion` | City religion |
| `Happiness` | City happiness |
| `Combat` | City combat |
| `Resources` | City resources |
| `Workers` | City workers |
| `Constructibles` | City constructibles |
| `Modifiers` | City modifiers |
| `TurnManager` | Turn management |

### City.Growth
| Method | Returns | Description |
|--------|---------|-------------|
| `turnsUntilGrowth` | `number` | Turns until next pop growth |
| `food` | `number` | Current food |
| `foodSurplus` | `number` | Food surplus |
| `calculateFoodConsumption()` | `number` | Food consumption |
| `getNextGrowthFoodThreshold()` | `number` | Food needed for growth |

### City.Production
| Method | Returns | Description |
|--------|---------|-------------|
| `getUnitProductionCost(unitType)` | `number` | Unit production cost |
| `getConstructibleProductionCost(type)` | `number` | Building production cost |
| `getProjectProductionCost(type)` | `number` | Project production cost |

### City.Yields
| Method | Returns | Description |
|--------|---------|-------------|
| `getYield(yieldType)` | `number` | Get specific yield |
| `getYields()` | `object` | Get all yields |
| `getNetYield(yieldType)` | `number` | Get net yield |
| `getPlotYields(x, y)` | `object` | Plot yields |
| `getResourceYields()` | `object` | Resource yields |
| `getTradeYields()` | `object` | Trade yields |

### City.Districts
| Method | Returns | Description |
|--------|---------|-------------|
| `getIds()` | `array` | All district IDs |
| `getIdsOfType(type)` | `array` | District IDs of type |
| `getNumDistricts()` | `number` | Number of districts |
| `getNumDistrictsOfType(type)` | `number` | Count of type |
| `hasDistrict(type)` | `boolean` | Has district type |

---

## Player.Units

`Players.get(id).Units` — Unit collection for a player.

| Method | Returns | Description |
|--------|---------|-------------|
| `getUnits()` | `array<Unit>` | All units as array |
| `getUnitIds()` | `array` | All unit IDs |
| `getNumUnitsOfType(type)` | `number` | Count of unit type |
| `canEverTrain(unitType)` | `boolean` | Can train unit type |
| `isUnitUnlocked(unitType)` | `boolean` | Is unit type unlocked |
| `isBuildDisabled(unitType)` | `boolean` | Is build disabled |
| `isBuildPermanentlyDisabled(unitType)` | `boolean` | Permanently disabled |
| `getCost(unitType)` | `number` | Unit cost |
| `getUnitTypesWithTag(tag)` | `array` | Unit types with tag |
| `getUnitTypesUnlockedWithTag(tag)` | `array` | Unlocked types with tag |

---

## Unit Instance

Properties of a unit from `Players.get(id).Units.getUnits()[i]`.

### Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | `object` | Unit ID |
| `localId` | `number` | Local unit ID |
| `name` | `string` | Unit name |
| `type` | `number` | Unit type (hash) |
| `location` | `{x, y}` | Current tile |
| `owner` | `number` | Owner player ID |
| `originalOwner` | `number` | Original owner |
| `age` | `number` | Unit age |
| `sightRange` | `number` | Vision range |
| `buildCharges` | `number` | Remaining build charges |
| `activityType` | `number` | Current activity |
| `embarkationType` | `number` | Embarkation type |
| `armyId` | `number` | Army ID |
| `formationID` | `number` | Formation ID |
| `formationUnitCount` | `number` | Units in formation |
| `originCityId` | `object` | City of origin |
| `operationQueueSize` | `number` | Queued operations |
| `operationTimer` | `number` | Operation timer |

### Boolean Checks
| Property | Description |
|----------|-------------|
| `isValid` | Is valid unit |
| `isDead` | Is dead |
| `isOnMap` | Is on map |
| `isCombat` | Is combat unit |
| `isGreatPerson` | Is great person |
| `isFortified` | Is fortified |
| `isEmbarked` | Is embarked |
| `isAutomated` | Is automated |
| `isBarbarian` | Is barbarian |
| `isBusy` | Is busy |
| `isPrivateer` | Is privateer |
| `isCommanderUnit` | Is commander |
| `isArmyCommander` | Is army commander |
| `isFleetCommander` | Is fleet commander |
| `isAerodromeCommander` | Is aerodrome commander |
| `isSquadronCommander` | Is squadron commander |
| `hasMoved` | Has moved this turn |
| `canMove` | Can move |
| `isReadyToMove` | Ready to move |
| `isReadyToSelect` | Ready to select |
| `isReadyToAutomate` | Ready to automate |
| `needsAttention` | Needs player attention |
| `hasPendingOperations` | Has pending operations |
| `canCyclePast` | Can cycle past |
| `hasAdjacentMove` | Has adjacent move available |
| `movementDisabledThisTurn` | Movement disabled |
| `canSeeThroughFeatures` | Can see through features |
| `canSeeThroughTerrain` | Can see through terrain |
| `hasHiddenVisibility` | Has hidden visibility |
| `noDefensiveBonus` | No defensive bonus |

### Sub-Objects
| Property | Methods |
|----------|---------|
| `Movement` | `getBaseMoves()`, `consumesAllMoves` |
| `Combat` | `getMeleeStrength()` |
| `Health` | `damageUnit(amount)`, `restoreUnitHealth()` |
| `Experience` | Experience system |
| `Religion` | Religious unit info |
| `Espionage` | Espionage actions |
| `GreatPerson` | Great person info |
| `Archaeology` | Archaeology actions |

---

## Player.Techs

`Players.get(id).Techs` — Technology tree.

| Method | Returns | Description |
|--------|---------|-------------|
| `getResearching()` | `number` | Currently researching tech |
| `getResearched()` | `array` | All researched techs |
| `getNumTechsUnlocked()` | `number` | Number of unlocked techs |
| `isNodeUnlocked(nodeType)` | `boolean` | Is tech unlocked |
| `getTreeType()` | `number` | Current tech tree type |
| `getTargetNode()` | `number` | Target research node |
| `getTurnsLeft()` | `number` | Turns left on current research |
| `getTurnsForNode(nodeType)` | `number` | Turns needed for tech |
| `getNodeCost(nodeType)` | `number` | Cost of tech |
| `getLastCompletedNodeType()` | `number` | Last completed tech |
| `getAllAvailableNodeTypes()` | `array` | Available techs to research |
| `getNodeUnlockDepthsRemaining()` | `number` | Unlock depths remaining |

---

## Player.Culture

`Players.get(id).Culture` — Civics and culture tree.

| Method | Returns | Description |
|--------|---------|-------------|
| `getResearching()` | `number` | Currently researching civic |
| `getResearched()` | `array` | All researched civics |
| `getNumCivicsUnlocked()` | `number` | Unlocked civics count |
| `isNodeUnlocked(nodeType)` | `boolean` | Is civic unlocked |
| `getActiveTree()` | `number` | Active culture tree |
| `getAvailableTrees()` | `array` | Available culture trees |
| `getTargetNode()` | `number` | Target civic node |
| `getTurnsLeft()` | `number` | Turns left |
| `getTurnsForNode(nodeType)` | `number` | Turns needed |
| `getNodeCost(nodeType)` | `number` | Civic cost |
| `getGovernmentType()` | `number` | Current government |
| `getActiveTraditions()` | `array` | Active traditions |
| `getUnlockedTraditions()` | `array` | Unlocked traditions |
| `getAllUnlockedTraditions()` | `array` | All unlocked traditions |
| `isTraditionActive(type)` | `boolean` | Is tradition active |
| `isTraditionUnlocked(type)` | `boolean` | Is tradition unlocked |
| `getChosenIdeology()` | `number` | Chosen ideology |
| `getNumCultureSlots()` | `number` | Culture slot count |
| `getNumAllCultureSlots()` | `number` | All culture slots |
| `getNumAgesResearched()` | `number` | Ages researched |

---

## Player.Treasury

`Players.get(id).Treasury` — Finances.

| Property/Method | Returns | Description |
|-----------------|---------|-------------|
| `goldBalance` | `number` | Current gold |
| `changeGoldBalance(amount)` | | Add/remove gold |
| `getMaintenanceForAllUnitsOfType(type)` | `number` | Unit maintenance |
| `getMaintenancePercentForAllUnitsOfType(type)` | `number` | Maintenance percent |

---

## Player.Diplomacy

`Players.get(id).Diplomacy` — Diplomatic relations.

| Method | Returns | Description |
|--------|---------|-------------|
| `hasMet(otherPlayerId)` | `boolean` | Has met player |
| `isAtWarWith(otherPlayerId)` | `boolean` | At war with player |
| `canDeclareWarOn(otherPlayerId)` | `boolean` | Can declare war |
| `canMakePeaceWith(otherPlayerId)` | `boolean` | Can make peace |
| `hasAllied(otherPlayerId)` | `boolean` | Is allied |
| `getRelationshipLevel(otherPlayerId)` | `number` | Relationship level |
| `getRelationshipLevelName(otherPlayerId)` | `string` | Relationship name |
| `getRelationshipEnum(otherPlayerId)` | `number` | Relationship enum |
| `getNumFavors(otherPlayerId)` | `number` | Favor count |
| `getNumGrievances(otherPlayerId)` | `number` | Grievance count |
| `getTotalTokens()` | `number` | Total diplomacy tokens |
| `getAvailableTokens()` | `number` | Available tokens |
| `getCommittedTokens()` | `number` | Committed tokens |
| `getEscrowTokens()` | `number` | Escrow tokens |
| `getReservedTokens()` | `number` | Reserved tokens |
| `getExhaustedTokens()` | `number` | Exhausted tokens |
| `forceDeclareWar(otherPlayerId)` | | Force declare war |
| `changeRelationshipLevel(playerId, delta)` | | Change relationship |
| `changeNumFavors(playerId, delta)` | | Change favors |
| `changeNumGrievances(playerId, delta)` | | Change grievances |

---

## Player.Resources

`Players.get(id).Resources` — Resource management.

| Method | Returns | Description |
|--------|---------|-------------|
| `getResources()` | `array` | All resources |
| `getCountResourcesToAssign()` | `number` | Resources to assign |
| `getCountImportedResources()` | `number` | Imported resource count |
| `getCityIDAssigned(resourceType)` | `number` | City assigned to resource |
| `getUnassignedResourceYieldBonus()` | `number` | Unassigned bonus |
| `isRessourceAssignmentLocked()` | `boolean` | Assignment locked |

---

## Player.Trade

`Players.get(id).Trade` — Trade routes.

| Method | Returns | Description |
|--------|---------|-------------|
| `getCurrentTradeRoutes()` | `array` | Active trade routes |
| `countPlayerTradeRoutes()` | `number` | Total trade routes |
| `countPlayerCityRoutes()` | `number` | City routes |
| `countPlayerTradeRoutesTo(playerId)` | `number` | Routes to player |
| `getTradeCapacityFromPlayer()` | `number` | Trade capacity |
| `canStartTradeRouteToCity(cityId)` | `boolean` | Can trade with city |
| `projectPossibleTradeRoutes()` | `array` | Possible routes |
| `projectPossibleTradeRoutesToCities()` | `array` | Routes to cities |
| `projectPossibleTradeRoutesToPlayers()` | `array` | Routes to players |

---

## Game

Game-level systems. Access via `Game.<SubSystem>`.

### Properties
| Property | Type | Description |
|----------|------|-------------|
| `turn` | `number` | Current turn number |
| `age` | `number` | Current age (hash) |
| `maxTurns` | `number` | Maximum turns |

### Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `getTurnDate()` | `string` | Current turn date string |
| `getHash(string)` | `number` | Hash a string |
| `getProperty(name)` | `any` | Get game property |

### Sub-Systems
| Property | Description |
|----------|-------------|
| `Game.Diplomacy` | Global diplomacy |
| `Game.VictoryManager` | Victory conditions |
| `Game.Religion` | Religion system |
| `Game.Combat` | Combat system |
| `Game.Trade` | Trade system |
| `Game.CityStates` | City-state system |
| `Game.Culture` | Global culture |
| `Game.Resources` | Global resources |
| `Game.CrisisManager` | Crisis events |
| `Game.RandomEvents` | Random events |
| `Game.EconomicRules` | Economic rules |
| `Game.Unlocks` | Unlock system |
| `Game.ProgressionTrees` | Progression trees |
| `Game.PlacementRules` | Placement rules |
| `Game.Summary` | Game summary |
| `Game.AgeProgressManager` | Age progression |
| `Game.IndependentPowers` | Independent powers |
| `Game.Modifiers` | Global modifiers |
| `Game.Notifications` | Notification system |
| `Game.DiplomacyDeals` | Diplomacy deals |
| `Game.DiplomacySessions` | Diplomacy sessions |
| `Game.CityCommands` | City command operations |
| `Game.CityOperations` | City operations |
| `Game.UnitCommands` | Unit command operations |
| `Game.UnitOperations` | Unit operations |
| `Game.PlayerOperations` | Player operations |

---

## Game.Diplomacy

| Method | Returns | Description |
|--------|---------|-------------|
| `hasMet(p1, p2)` | `boolean` | Have players met |
| `hasTeammate(p1, p2)` | `boolean` | Are teammates |
| `getActiveEvents()` | `array` | Active diplomatic events |
| `getWarData(p1, p2)` | `object` | War data between players |
| `getPlayerHistory(playerId)` | `object` | Diplomatic history |
| `getPlayerEvents(playerId)` | `array` | Player's diplomatic events |
| `getRecentlyEndedDiplomaticEvents()` | `array` | Recently ended events |
| `getVictories()` | `array` | Diplomatic victories |

---

## Game.VictoryManager

| Method | Returns | Description |
|--------|---------|-------------|
| `getVictories()` | `array` | Current victories |
| `getDefeats()` | `array` | Current defeats |
| `getVictoryProgress()` | `object` | Victory progress data |
| `getAgeOver()` | `boolean` | Is current age over |
| `getConfiguration()` | `object` | Victory configuration |
| `getVictoryEnabledPlayers()` | `array` | Victory-eligible players |
| `getDefeatEnabledPlayers()` | `array` | Defeat-eligible players |
| `getPreviousAgeVictories()` | `array` | Previous age victories |

---

## Game.Religion

| Method | Returns | Description |
|--------|---------|-------------|
| `hasBeenFounded(religionType)` | `boolean` | Has religion been founded |
| `getPlayerFromReligion(religionType)` | `number` | Player who founded religion |
| `isBeliefClaimable(beliefType)` | `boolean` | Is belief available |
| `canHaveBelief(beliefType)` | `boolean` | Can have belief |
| `isInSomePantheon(beliefType)` | `boolean` | In any pantheon |
| `isInSomeReligion(beliefType)` | `boolean` | In any religion |

---

## Game.Combat

| Method | Returns | Description |
|--------|---------|-------------|
| `simulateAttackAsync(attacker, defender)` | `object` | Simulate attack |
| `testAttackInto(attacker, x, y)` | `object` | Test attack into tile |
| `getBestDefender(x, y)` | `object` | Best defender at tile |
| `getDefensibleDistrict(x, y)` | `object` | Defensible district at tile |
| `detonateWMD(x, y, type, player)` | | Detonate WMD |

---

## Game.Trade

| Method | Returns | Description |
|--------|---------|-------------|
| `getCityRoutes()` | `array` | All city trade routes |
| `findTradeRouteBetween(city1, city2)` | `object` | Route between cities |
| `findTradeRouteByID(routeId)` | `object` | Route by ID |
| `getTradeRouteName(routeId)` | `string` | Route name |
| `getCityGraphEdges()` | `array` | Trade graph edges |

---

## Game.CityStates

| Method | Returns | Description |
|--------|---------|-------------|
| `hasBeenChosen(type)` | `boolean` | City state chosen |
| `getBonusType(type)` | `number` | Bonus type |
| `isBonusActive(type, playerId)` | `boolean` | Is bonus active |
| `canHaveBonus(type)` | `boolean` | Can have bonus |
| `hasAssignedBonus(type)` | `boolean` | Has assigned bonus |

---

## GameContext

Turn management and game flow control.

| Method | Returns | Description |
|--------|---------|-------------|
| `sendTurnComplete()` | | End turn |
| `sendUnreadyTurn()` | | Unready turn |
| `sendRetireRequest()` | | Retire from game |
| `sendPauseRequest()` | | Pause game |
| `sendGameQuery(query)` | | Send game query |
| `hasSentTurnComplete` | `boolean` | Has sent turn complete |
| `hasSentRetire` | `boolean` | Has sent retire |
| `hasRequestedPause` | `boolean` | Has requested pause |
| `hasSentTurnUnreadyThisTurn` | `boolean` | Unreadied this turn |

---

## Configuration

Game configuration access.

| Method | Returns | Description |
|--------|---------|-------------|
| `getGame()` | `object` | Game configuration |
| `getMap()` | `object` | Map configuration |
| `getPlayer(playerId)` | `object` | Player configuration |
| `getUser()` | `object` | User configuration |
| `getDebug()` | `object` | Debug configuration |
| `getXR()` | `object` | XR configuration |
| `editGame()` | `object` | Edit game config |
| `editMap()` | `object` | Edit map config |
| `editPlayer(playerId)` | `object` | Edit player config |

### Configuration.getGame()
| Method | Returns | Description |
|--------|---------|-------------|
| `getValue(key)` | `any` | Get config value |
| `getValues()` | `object` | All config values |
| `hasValue(key)` | `boolean` | Has config key |
| `getParticipatingPlayerCount()` | `number` | Player count |
| `isValidPlayer(id)` | `boolean` | Valid player |
| `getGameModeString()` | `string` | Game mode |
| `getPreviousAge()` | `number` | Previous age |

---

## UI

User interface control. Large API surface — most methods are for internal UI management.

### Useful Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `isInGame()` | `boolean` | Is in active game |
| `isInLoading()` | `boolean` | Is loading |
| `isInShell()` | `boolean` | Is in main menu |
| `isMultiplayer()` | `boolean` | Is multiplayer game |
| `getIcon(name)` | `string` | Get icon by name |
| `getIconURL(name)` | `string` | Get icon URL |
| `setClipboardText(text)` | | Copy text to clipboard |
| `random()` | `number` | Random number |
| `randomInt(min, max)` | `number` | Random integer |
| `debugPrint(message)` | | Print debug message |

---

## WorldBuilder

Limited world builder access.

| Method | Description |
|--------|-------------|
| `startBlock()` | Start a world builder block |
| `endBlock()` | End a world builder block |

---

## Useful Patterns

### Get all player data as JSON
```js
JSON.stringify(Players.getAliveMajorIds().map(id => {
  const p = Players.get(id);
  return {
    id, civ: p.civilizationFullName,
    gold: p.Treasury.goldBalance,
    cities: p.Cities.getCities().map(c => ({
      name: c.name, x: c.location.x, y: c.location.y,
      population: c.population, isCapital: c.isCapital
    }))
  };
}), null, 2)
```

### Scan map for continents
```js
const continents = new Map();
const w = GameplayMap.getGridWidth();
const h = GameplayMap.getGridHeight();
for (let x = 0; x < w; x += 5) {
  for (let y = 0; y < h; y += 5) {
    const c = GameplayMap.getContinentType(x, y);
    if (c !== -1 && !continents.has(c))
      continents.set(c, {x, y});
  }
}
let r = [];
continents.forEach((v, k) => r.push({continent: k, sampleX: v.x, sampleY: v.y}));
JSON.stringify({count: continents.size, continents: r}, null, 2)
```

### Check diplomatic relationships between all players
```js
let r = [];
const ids = Players.getAliveMajorIds();
ids.forEach(id => {
  const p = Players.get(id);
  ids.forEach(otherId => {
    if (id < otherId && p.Diplomacy.hasMet(otherId)) {
      r.push({
        p1: id, p2: otherId,
        level: p.Diplomacy.getRelationshipLevelName(otherId),
        atWar: p.Diplomacy.isAtWarWith(otherId)
      });
    }
  });
});
JSON.stringify(r, null, 2)
```

### Discover methods on any object
```js
// Instance properties
JSON.stringify(Object.getOwnPropertyNames(someObject).sort())

// Prototype methods (the useful ones)
JSON.stringify(Object.getOwnPropertyNames(Object.getPrototypeOf(someObject)).sort())
```

### Grant gold to a player
```js
Players.get(0).Treasury.changeGoldBalance(1000)
```

---

## Contributing

This API library is **community-driven**. The Civ 7 debug API is undocumented, so every discovery helps.

### How to Contribute

1. **Fork the repository** and create a branch
2. **Add your findings** to this file following the existing format
3. **Include working examples** — verified against a live game
4. **Open a pull request** with a description of what you discovered

### What to Contribute

- **New API methods** you've found through introspection
- **Return type corrections** — if a method returns something different than documented
- **Working code patterns** that solve common problems
- **Parameter details** — many methods have undocumented parameters
- **Enum values** — what do the numeric type/terrain/feature constants mean?
- **Age-specific APIs** — some APIs may differ between Antiquity, Exploration, and Modern ages

### Discovery Tips

Use these patterns to find new API surface:

```js
// List all properties on an object
JSON.stringify(Object.getOwnPropertyNames(someObject).sort())

// List all prototype methods
JSON.stringify(Object.getOwnPropertyNames(Object.getPrototypeOf(someObject)).sort())

// Check if something exists
typeof SomePossibleGlobal

// Probe a method's behavior
try { someMethod() } catch(e) { e.message }
```

### AI Agents: Help Build This Library

If you're an AI agent using the MCP server and you discover a new API call or pattern that works, **suggest to the user that they open a pull request** to add it to this file. The more we document, the more useful this becomes for everyone.
