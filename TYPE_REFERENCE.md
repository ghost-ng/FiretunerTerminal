# Civ7 JavaScript Type Reference

Complete type information extracted from Civilization 7 source maps. This data powers the terminal's Tab completion and can serve as a reference when writing debug commands.

> **18 globals** | **40 sub-objects** | **531 methods** | **252 properties**

## Table of Contents

### Globals

- [Configuration](#configuration)
- [Controls](#controls)
- [Database](#database)
- [Districts](#districts)
- [Game](#game)
- [GameContext](#gamecontext)
- [GameInfo](#gameinfo)
- [GameplayMap](#gameplaymap)
- [Loading](#loading)
- [Locale](#locale)
- [MapCities](#mapcities)
- [MapConstructibles](#mapconstructibles)
- [MapUnits](#mapunits)
- [Players](#players)
- [UI](#ui)
- [WorldBuilder](#worldbuilder)
- [WorldUI](#worldui)
- [engine](#engine)

### Player Sub-Objects

Accessed via `Players.get(id).<SubObject>`

- [AdvancedStart](#advancedstart)
- [AgeProgressManager](#ageprogressmanager)
- [BuildQueue](#buildqueue)
- [Cities](#cities)
- [CityCommands](#citycommands)
- [CityOperations](#cityoperations)
- [CityStates](#citystates)
- [Combat](#combat)
- [Constructibles](#constructibles)
- [CrisisManager](#crisismanager)
- [Culture](#culture)
- [Diplomacy](#diplomacy)
- [DiplomacyDeals](#diplomacydeals)
- [DiplomacySessions](#diplomacysessions)
- [DiplomacyTreasury](#diplomacytreasury)
- [Districts](#districts)
- [EconomicRules](#economicrules)
- [Experience](#experience)
- [Health](#health)
- [IndependentPowers](#independentpowers)
- [Influence](#influence)
- [LegacyPaths](#legacypaths)
- [Movement](#movement)
- [Notifications](#notifications)
- [PlacementRules](#placementrules)
- [PlayerOperations](#playeroperations)
- [ProgressionTrees](#progressiontrees)
- [RandomEvents](#randomevents)
- [Religion](#religion)
- [Resources](#resources)
- [Stats](#stats)
- [Techs](#techs)
- [Trade](#trade)
- [Treasury](#treasury)
- [UnitCommands](#unitcommands)
- [UnitOperations](#unitoperations)
- [Units](#units)
- [Unlocks](#unlocks)
- [VictoryManager](#victorymanager)
- [Yields](#yields)

---

## Globals

### Configuration

#### Methods

| Method | Signature |
|--------|-----------|
| `editGame` | `editGame() → ConfigurationGameMutator` |
| `editMap` | `editMap()` |
| `editPlayer` | `editPlayer(localPlayerID) → ConfigurationPlayerMutator` |
| `getGame` | `getGame() → ConfigurationGameAccessor` |
| `getGameValue` | `getGameValue(arg0)` |
| `getMap` | `getMap() → ConfigurationMapAccessor` |
| `getMapValue` | `getMapValue(arg0) → number` |
| `getPlayer` | `getPlayer(defeatedPlayer) → ConfigurationPlayerAccessor` |
| `getUser` | `getUser() → ConfigurationUserLibrary` |
| `getXR` | `getXR()` |

#### Properties

| Property | Type |
|----------|------|
| `isNetworkMultiplayer` | — |
| `isSavedGame` | — |
| `leaderName` | — |
| `leaderTypeName` | — |
| `previousAgeCount` | — |
| `script` | — |

### Controls

#### Methods

| Method | Signature |
|--------|-----------|
| `appendChild` | `appendChild(accessibilityContainer)` |
| `define` | `define(EditorKeyboardBindingPanelTagName, {
		createInstance)` |
| `getDefinition` | `getDefinition(typeName) → ComponentDefinition` |
| `initializeComponents` | `initializeComponents()` |
| `preloadImage` | `preloadImage(url, arg1)` |
| `removeChild` | `removeChild(arg0)` |

#### Properties

| Property | Type |
|----------|------|
| `children` | — |
| `classList` | — |

### Database

#### Methods

| Method | Signature |
|--------|-----------|
| `changes` | `changes(dbName)` |
| `makeHash` | `makeHash(UnitPromotionDisciplineType) → number` |
| `query` | `query(arg0, SQL, TraditionType as Type, ReasonType FROM LeaderCivilizationBias")` |
| `register` | `register()` |

#### Properties

| Property | Type |
|----------|------|
| `DbName` | — |
| `DbRow` | — |

### Districts

#### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(districtId) → District` |
| `getAtLocation` | `getAtLocation(plotCoordinate) → District` |
| `getDistrictHealth` | `getDistrictHealth(location)` |
| `getDistrictIds` | `getDistrictIds()` |
| `getDistrictIsBesieged` | `getDistrictIsBesieged(location)` |
| `getDistrictMaxHealth` | `getDistrictMaxHealth(location)` |
| `getFreeConstructible` | `getFreeConstructible(plotCoordinate, localPlayerID)` |
| `getIdAtLocation` | `getIdAtLocation(loc)` |
| `getIdsOfType` | `getIdsOfType(districtType)` |
| `getIdsOfTypes` | `getIdsOfTypes(arg0)` |
| `getLocations` | `getLocations(districtIdsRural) → PlotCoord[]` |
| `lookup` | `lookup(AdjacentDistrict)` |

#### Properties

| Property | Type |
|----------|------|
| `cityCenter` | — |

### Game

#### Methods

| Method | Signature |
|--------|-----------|
| `bind` | `bind(arg0)` |
| `cancel` | `cancel()` |
| `getBenchmarkType` | `getBenchmarkType()` |
| `getDebugUiVisiblity` | `getDebugUiVisiblity()` |
| `getHash` | `getHash(itemBankName) → number` |
| `getTurnDate` | `getTurnDate() → string` |
| `isRunning` | `isRunning()` |
| `randomRange` | `randomRange(arg0, gridHeight - Y_PADDING - 1)` |
| `setDebugUiVisiblity` | `setDebugUiVisiblity(arg0)` |
| `setLightweightGraphPosition` | `setLightweightGraphPosition(x, y, width, height)` |
| `start` | `start(startParameters)` |

#### Properties

| Property | Type |
|----------|------|
| `ContentType` | — |
| `Directory` | — |
| `FileName` | — |
| `IsAutosave` | — |
| `IsQuicksave` | — |
| `Location` | — |
| `LocationCategories` | — |
| `Summary` | — |
| `Type` | — |
| `age` | AgeType |
| `maxTurns` | — |
| `playerScores` | — |
| `turn` | number |
| `updateCallback` | — |

### GameContext

#### Methods

| Method | Signature |
|--------|-----------|
| `hasSentRetire` | `hasSentRetire()` |
| `hasSentTurnComplete` | `hasSentTurnComplete()` |
| `hasSentTurnUnreadyThisTurn` | `hasSentTurnUnreadyThisTurn()` |
| `sendPauseRequest` | `sendPauseRequest(arg0)` |
| `sendRetireRequest` | `sendRetireRequest()` |
| `sendTurnComplete` | `sendTurnComplete()` |
| `sendUnreadyTurn` | `sendUnreadyTurn()` |

#### Properties

| Property | Type |
|----------|------|
| `localObserverID` | PlayerId |
| `localPlayerID` | PlayerId |

### GameInfo

#### Properties

| Property | Type |
|----------|------|
| `Adjacency_YieldChanges` | — |
| `AdvancedStartDeckCardEntries` | DefinitionCollection<AdvancedStartDeckCardEntryDefinition> |
| `AdvancedStartParameters` | — |
| `AdvisorySubjects` | — |
| `AgeProgressionDarkAgeRewardInfos` | — |
| `AgeProgressionMilestoneRewards` | — |
| `AgeProgressionMilestones` | — |
| `AgeProgressionRewards` | AgeProgressionRewardDefinition |
| `Ages` | AgeDefinition |
| `Attributes` | — |
| `BeliefClasses` | — |
| `Beliefs` | BeliefDefinition |
| `Biomes` | BiomeType |
| `Buildings` | BuildingDefinition |
| `CityStateBonuses` | CityStateBonusDefinition |
| `CivilizationTraits` | — |
| `Civilizations` | string |
| `CivilopediaPageChapterHeaders` | — |
| `CivilopediaPageChapterParagraphs` | — |
| `CivilopediaPageExcludes` | — |
| `CivilopediaPageGroupExcludes` | — |
| `CivilopediaPageGroupQueries` | — |
| `CivilopediaPageGroups` | — |
| `CivilopediaPageLayoutChapterContentQueries` | — |
| `CivilopediaPageLayoutChapters` | — |
| `CivilopediaPageLayouts` | — |
| `CivilopediaPageQueries` | — |
| `CivilopediaPageSearchTermQueries` | — |
| `CivilopediaPageSearchTerms` | — |
| `CivilopediaPageSidebarPanels` | — |
| `CivilopediaPages` | — |
| `CivilopediaSectionExcludes` | — |
| `CivilopediaSections` | — |
| `ConstructibleModifiers` | — |
| `Constructible_Adjacencies` | — |
| `Constructible_Maintenances` | — |
| `Constructible_WarehouseYields` | — |
| `Constructible_YieldChanges` | — |
| `Continents` | — |
| `Defeats` | — |
| `Difficulties` | — |
| `DiplomacyActions` | DiplomacyActionDefinition |
| `DiplomacyStatementFrames` | — |
| `DiplomacyStatementSelections` | — |
| `DiplomacyStatements` | — |
| `DiplomaticProjects_UI_Data` | — |
| `DiscoverySiftingImprovements` | — |
| `DisplayQueuePriorities` | — |
| `EndGameMovies` | — |
| `FeatureClasses` | — |
| `Feature_NaturalWonders` | — |
| `Features` | FeatureType |
| `GameSpeeds` | — |
| `GlobalParameters` | GlobalParameterDefinition |
| `GoldenAges` | GoldenAgeDefinition |
| `Governments` | GovernmentDefinition |
| `GreatWork_YieldChanges` | GreatWork_YieldChangeDefinition |
| `GreatWorks` | GreatWorkDefinition |
| `ID` | — |
| `Ideologies` | — |
| `Improvements` | ImprovementDefinition |
| `Independents` | — |
| `InterfaceModes` | InterfaceModeDefinition |
| `KeywordAbilities` | — |
| `LeaderInfo` | — |
| `Leaders` | LeaderDefinition |
| `LegacyCivilizationTraits` | CivilizationTraitDefinition |
| `LegacyCivilizations` | — |
| `LoadingInfo_Civilizations` | — |
| `LoadingInfo_Leaders` | — |
| `MapIslandBehavior` | — |
| `MapResourceMinimumAmountModifier` | — |
| `Maps` | — |
| `Mementos` | — |
| `ModifierStrings` | — |
| `Modifiers` | — |
| `NarrativeDisplay_Civilizations` | — |
| `NarrativeRewardIcons` | NarrativeRewardIconDefinition[] |
| `NarrativeStories` | NarrativeStoryDefinition |
| `NarrativeStory_Links` | NarrativeStory_LinkDefinition[] |
| `NarrativeStory_RewardIcons` | — |
| `NotificationSounds` | — |
| `PlotEffects` | PlotEffectDefinition |
| `ProgressionTreeNodeUnlocks` | ProgressionTreeNodeUnlockDefinition |
| `ProgressionTreeNodes` | ProgressionTreeNodeDefinition |
| `Projects` | ProjectDefinition |
| `RandomEventUI` | — |
| `Religions` | ReligionDefinition |
| `ResourceClasses` | — |
| `Resource_Distribution` | — |
| `Resource_YieldChanges` | — |
| `Routes` | — |
| `StartBiasAdjacentToCoasts` | — |
| `StartBiasBiomes` | string |
| `StartBiasFeatureClasses` | — |
| `StartBiasLakes` | — |
| `StartBiasNaturalWonders` | — |
| `StartBiasResources` | — |
| `StartBiasRivers` | — |
| `StartBiasTerrains` | — |
| `StartingGovernments` | — |
| `Terrains` | TerrainType |
| `TradeYields` | TradeYieldDefinition |
| `TraditionModifiers` | — |
| `Traditions` | TraditionDefinition |
| `TypeQuotes` | — |
| `TypeTags` | — |
| `Types` | — |
| `UniqueQuarters` | — |
| `UnitAbilities` | — |
| `UnitPromotionClassSets` | — |
| `UnitPromotionDisciplineDetails` | UnitPromotionDisciplineDetailDefinition[] |
| `UnitPromotionDisciplines` | UnitPromotionDisciplineDefinition |
| `UnitPromotions` | — |
| `UnitReplaces` | UnitReplaceDefinition[] |
| `UnitUpgrades` | — |
| `Unit_Costs` | — |
| `Unit_RequiredConstructibles` | — |
| `Unit_ShadowReplacements` | — |
| `Unit_Stats` | Unit_StatDefinition |
| `UnlockRequirements` | — |
| `UnlockRewards` | — |
| `Victories` | VictoryDefinition |
| `VictoryCinematics` | — |
| `Wonders` | WonderDefinition |
| `isLiveEventGame` | — |
| `missingMods` | — |
| `unownedMods` | — |

### GameplayMap

#### Methods

| Method | Signature |
|--------|-----------|
| `findSecondContinent` | `findSecondContinent(iX, iY, arg2)` |
| `getAdjacentPlotLocation` | `getAdjacentPlotLocation(plotCursorCoords, DIRECTION_WEST) → PlotCoord` |
| `getAppeal` | `getAppeal(x, y)` |
| `getAreaId` | `getAreaId(iAdjacentX, iAdjacentY)` |
| `getAreaIsWater` | `getAreaIsWater(iAdjacentX, iAdjacentY)` |
| `getBiomeType` | `getBiomeType(xCoord, yCoord) → BiomeType` |
| `getContinentType` | `getContinentType(hoveredX, hoveredY)` |
| `getDirectionToPlot` | `getDirectionToPlot(sourcePlotLocation, targetPlotLocation) → DirectionTypes` |
| `getElevation` | `getElevation(iAdjacentX, iAdjacentY) → number` |
| `getFeatureClassType` | `getFeatureClassType(x, y)` |
| `getFeatureType` | `getFeatureType(iX, iY) → FeatureType` |
| `getGridHeight` | `getGridHeight() → number` |
| `getGridWidth` | `getGridWidth() → number` |
| `getHemisphere` | `getHemisphere(iX)` |
| `getIndexFromLocation` | `getIndexFromLocation(independentLocation) → number` |
| `getIndexFromXY` | `getIndexFromXY(iAdjacentX, iAdjacentY) → number` |
| `getLandmassRegionId` | `getLandmassRegionId(iX, iY)` |
| `getLocationFromIndex` | `getLocationFromIndex(selectedResourceValue) → float2` |
| `getMapSize` | `getMapSize()` |
| `getOwner` | `getOwner(iX, iY) → PlayerId` |
| `getOwnerHostility` | `getOwnerHostility(x, y, localPlayerID) → string` |
| `getOwnerName` | `getOwnerName(x, y)` |
| `getOwningCityFromXY` | `getOwningCityFromXY(x, y) → ComponentID` |
| `getPlotDistance` | `getPlotDistance(iContinentLeftEdge, iContinentBottomRow, iContinentCenterX, iContinentCenterY) → number` |
| `getPlotIndicesInRadius` | `getPlotIndicesInRadius(iX, iY, minRange) → number[]` |
| `getPlotLatitude` | `getPlotLatitude(iX, iY) → number` |
| `getPrimaryHemisphere` | `getPrimaryHemisphere()` |
| `getRainfall` | `getRainfall(iX, iY) → number` |
| `getRandomSeed` | `getRandomSeed()` |
| `getRegionId` | `getRegionId(x, y)` |
| `getResourceType` | `getResourceType(iAdjacentX, iAdjacentY) → ResourceType` |
| `getRevealedState` | `getRevealedState(localObserverID, x, y) → RevealedStates` |
| `getRevealedStates` | `getRevealedStates(localPlayerID)` |
| `getRiverName` | `getRiverName(x, y) → string` |
| `getRiverType` | `getRiverType(iAdjacentX, iAdjacentY) → RiverTypes` |
| `getRouteType` | `getRouteType(x, y) → RouteType` |
| `getTerrainType` | `getTerrainType(iX, iY) → TerrainType` |
| `getVolcanoName` | `getVolcanoName(x, y)` |
| `getYield` | `getYield(x, y, YieldType, playerID) → number` |
| `getYields` | `getYields(plotIndex, localPlayerID)` |
| `getYieldsWithCity` | `getYieldsWithCity(location, cityID)` |
| `hasPlotTag` | `hasPlotTag(iAdjacentX, iAdjacentY, PLOT_TAG_ISLAND)` |
| `isAdjacentToFeature` | `isAdjacentToFeature(iX, iY, featIdx)` |
| `isAdjacentToLand` | `isAdjacentToLand(iX, iY)` |
| `isAdjacentToRivers` | `isAdjacentToRivers(iX, iY, arg2)` |
| `isAdjacentToShallowWater` | `isAdjacentToShallowWater(iAdjacentX, iAdjacentY)` |
| `isCityWithinMinimumDistance` | `isCityWithinMinimumDistance(x, y)` |
| `isCliffCrossing` | `isCliffCrossing(iX, iY, iDirection)` |
| `isCoastalLand` | `isCoastalLand(iX, iY)` |
| `isFerry` | `isFerry(x, y) → boolean` |
| `isFreshWater` | `isFreshWater(x, y)` |
| `isImpassable` | `isImpassable(iAdjacentX, iAdjacentY)` |
| `isLake` | `isLake(iX, iY)` |
| `isMountain` | `isMountain(iX, iY)` |
| `isNaturalWonder` | `isNaturalWonder(iAdjacentX, iAdjacentY)` |
| `isNavigableRiver` | `isNavigableRiver(xCoord, yCoord)` |
| `isPlotInAdvancedStartRegion` | `isPlotInAdvancedStartRegion(localPlayerID, x, y)` |
| `isRiver` | `isRiver(iX, iY)` |
| `isValidLocation` | `isValidLocation(plotCursorCoords)` |
| `isVolcano` | `isVolcano(x, y)` |
| `isVolcanoActive` | `isVolcanoActive(x, y)` |
| `isWater` | `isWater(iAdjacentX, iAdjacentY)` |

### Loading

#### Methods

| Method | Signature |
|--------|-----------|
| `runWhenFinished` | `runWhenFinished(onPullCurtain)` |
| `runWhenInitialized` | `runWhenInitialized(arg0)` |
| `runWhenLoaded` | `runWhenLoaded(arg0)` |

#### Properties

| Property | Type |
|----------|------|
| `isFinished` | — |
| `isInitialized` | — |
| `isLoaded` | — |
| `onInitialScriptAdded` | — |
| `processInitialScriptsRAF` | — |
| `whenFinished` | — |
| `whenInitialized` | — |
| `whenLoaded` | — |

### Locale

#### Methods

| Method | Signature |
|--------|-----------|
| `changeAudioLanguageOption` | `changeAudioLanguageOption(selectedAudioIdx)` |
| `changeDisplayLanguageOption` | `changeDisplayLanguageOption(selectedDisplayIdx)` |
| `compare` | `compare(Description ?? "", Description ?? "")` |
| `compose` | `compose(volcanoDetailsKey, settlementInDistantLands, completionScore, theirInfluenceBonus) → string` |
| `fromUGC` | `fromUGC(baseReligionName, customReligionName)` |
| `getAudioLanguageOptionNames` | `getAudioLanguageOptionNames()` |
| `getCurrentAudioLanguageOption` | `getCurrentAudioLanguageOption()` |
| `getCurrentDisplayLanguageOption` | `getCurrentDisplayLanguageOption()` |
| `getCurrentDisplayLocale` | `getCurrentDisplayLocale()` |
| `getCurrentLocale` | `getCurrentLocale()` |
| `getDisplayLanguageOptionNames` | `getDisplayLanguageOptionNames()` |
| `getIconTagsForLocStrings` | `getIconTagsForLocStrings(locStrings)` |
| `keyExists` | `keyExists(baseDiplomacyMessageString + "_ACCEPTED_" + otherLeaderName)` |
| `plainText` | `plainText(string)` |
| `stylize` | `stylize(arg0, value > 0 ? "text-positive", goldenAgeTurnsLeft, theirInfluenceBonus) → string` |
| `toNumber` | `toNumber(value, arg1) → string` |
| `toPercent` | `toPercent(victoryProgression / maxAgeProgress)` |
| `toRomanNumeral` | `toRomanNumeral(depthUnlocked + 1) → string` |
| `toUpper` | `toUpper(StoryTitle)` |
| `unpack` | `unpack(hostCivilizationName)` |

#### Properties

| Property | Type |
|----------|------|
| `Compose` | — |
| `Stylize` | — |

### MapCities

#### Methods

| Method | Signature |
|--------|-----------|
| `getCity` | `getCity(iX, iY) → any` |
| `getDistrict` | `getDistrict(iX, iY) → ComponentID` |

### MapConstructibles

#### Methods

| Method | Signature |
|--------|-----------|
| `addDiscovery` | `addDiscovery(iX, iY, IMPROVEMENT_SHIPWRECK, discoveryType)` |
| `addDiscoveryType` | `addDiscoveryType(arg0)` |
| `addIndependentType` | `addIndependentType(x, y)` |
| `addRoute` | `addRoute(x, y, arg2)` |
| `getConstructibles` | `getConstructibles(hoveredX, hoveredY) → ComponentID[]` |
| `getHiddenFilteredConstructibles` | `getHiddenFilteredConstructibles(x, y)` |
| `getReplaceableConstructible` | `getReplaceableConstructible(x, y) → number` |
| `removeRoute` | `removeRoute(x, y)` |

### MapUnits

#### Methods

| Method | Signature |
|--------|-----------|
| `getUnits` | `getUnits(x, y) → ComponentID[]` |

### Players

#### Methods

| Method | Signature |
|--------|-----------|
| `entries` | `entries()` |
| `filter` | `filter(arg0)` |
| `forEach` | `forEach(arg0)` |
| `get` | `get(_selectedPlayerID) → PlayerLibrary` |
| `getAlive` | `getAlive() → PlayerLibrary[]` |
| `getAliveIds` | `getAliveIds()` |
| `getAliveMajorIds` | `getAliveMajorIds()` |
| `getEverAlive` | `getEverAlive() → PlayerLibrary[]` |
| `getWasEverAliveMajorIds` | `getWasEverAliveMajorIds()` |
| `includes` | `includes(localPlayerID)` |
| `isAI` | `isAI(arg0)` |
| `isAlive` | `isAlive(localPlayerID)` |
| `isHuman` | `isHuman(localPlayerID)` |
| `isParticipant` | `isParticipant(localPlayerID)` |
| `isValid` | `isValid(_selectedPlayerID)` |
| `push` | `push(playerConfig)` |
| `some` | `some(arg0)` |

#### Properties

| Property | Type |
|----------|------|
| `AI` | — |
| `Advisory` | — |
| `length` | — |
| `maxPlayers` | — |

### UI

#### Methods

| Method | Signature |
|--------|-----------|
| `SetShowIntroSequences` | `SetShowIntroSequences(value ? 1)` |
| `activityHostMPGameConfirmed` | `activityHostMPGameConfirmed()` |
| `activityLoadLastSaveGameConfirmed` | `activityLoadLastSaveGameConfirmed()` |
| `addBackgroundLayer` | `addBackgroundLayer(arg0, arg1)` |
| `addMaskedBackgroundLayer` | `addMaskedBackgroundLayer(backgroundName, arg1, {
					stretch)` |
| `areAdaptiveTriggersAvailable` | `areAdaptiveTriggersAvailable()` |
| `beginProfiling` | `beginProfiling(arg0)` |
| `canDisplayKeyboard` | `canDisplayKeyboard()` |
| `canExitToDesktop` | `canExitToDesktop()` |
| `canSetAutoScaling` | `canSetAutoScaling()` |
| `canSkipMovies` | `canSkipMovies()` |
| `clearBackground` | `clearBackground()` |
| `commitApplicationOptions` | `commitApplicationOptions()` |
| `commitNetworkOptions` | `commitNetworkOptions()` |
| `createFixedMarker` | `createFixedMarker({ x, y, z)` |
| `createModelGroup` | `createModelGroup(arg0)` |
| `createOverlayGroup` | `createOverlayGroup(arg0, UNIT_MOVEMENT_SKIRT, { x)` |
| `createSpriteGrid` | `createSpriteGrid(name + "_Background", FixedBillboard)` |
| `defaultApplicationOptions` | `defaultApplicationOptions()` |
| `defaultAudioOptions` | `defaultAudioOptions()` |
| `defaultTutorialOptions` | `defaultTutorialOptions()` |
| `defaultUserOptions` | `defaultUserOptions()` |
| `displayKeyboard` | `displayKeyboard(value, arg1)` |
| `endProfiling` | `endProfiling(refreshGameOptionsProfilingHandle)` |
| `exposeShowIntroVideoOption` | `exposeShowIntroVideoOption()` |
| `favorSpeedOverQuality` | `favorSpeedOverQuality()` |
| `getApplicationOption` | `getApplicationOption(arg0, arg1)` |
| `getChatIconGroups` | `getChatIconGroups()` |
| `getChatIcons` | `getChatIcons(groupId)` |
| `getCurrentGraphicsProfile` | `getCurrentGraphicsProfile()` |
| `getCursorType` | `getCursorType()` |
| `getCursorURL` | `getCursorURL()` |
| `getDiploRibbonIndex` | `getDiploRibbonIndex()` |
| `getDirection` | `getDirection(x, y)` |
| `getGameLoadingState` | `getGameLoadingState()` |
| `getGraphicsProfile` | `getGraphicsProfile(profile as number)` |
| `getIMEConfirmationValueLocation` | `getIMEConfirmationValueLocation()` |
| `getIcon` | `getIcon(ReligionType, arg1)` |
| `getIconBLP` | `getIconBLP(ConstructibleType, arg1) → string` |
| `getIconCSS` | `getIconCSS(selectedReligionType, context ? context) → string` |
| `getIconURL` | `getIconURL(civID == "RANDOM" ? "CIVILIZATION_RANDOM", indCivType == "MILITARISTIC" ? "PLAYER_RELATIONSHIP") → string` |
| `getOOBEGraphicsRestart` | `getOOBEGraphicsRestart()` |
| `getOption` | `getOption(RIBBON_DISPLAY_OPTION_SET, RIBBON_DISPLAY_OPTION_TYPE, optionName) → number` |
| `getPlotAt` | `getPlotAt(controllerCursor, arg1)` |
| `getPlotLocation` | `getPlotLocation(desiredDestination, { x, TERRAIN)` |
| `getSafeAreaMargins` | `getSafeAreaMargins() → SafeAreaMargins` |
| `getScreenPlotPos` | `getScreenPlotPos(plotCursorCoords)` |
| `getScreenPos` | `getScreenPos(controllerCursor)` |
| `getViewExperience` | `getViewExperience()` |
| `getVirtualKeyboardType` | `getVirtualKeyboardType()` |
| `hasViewExperience` | `hasViewExperience()` |
| `hash` | `hash(arg0)` |
| `hideCursor` | `hideCursor()` |
| `isAssetLoaded` | `isAssetLoaded(currentPreloadingAsset)` |
| `isAudioCursorEnabled` | `isAudioCursorEnabled()` |
| `isClipboardAvailable` | `isClipboardAvailable()` |
| `isCursorLocked` | `isCursorLocked()` |
| `isDebugPlotInfoVisible` | `isDebugPlotInfoVisible()` |
| `isFirstBoot` | `isFirstBoot()` |
| `isHostAPC` | `isHostAPC()` |
| `isInGame` | `isInGame()` |
| `isInLoading` | `isInLoading()` |
| `isInShell` | `isInShell()` |
| `isMouseAvailable` | `isMouseAvailable()` |
| `isMultiplayer` | `isMultiplayer()` |
| `isNetworkBuild` | `isNetworkBuild()` |
| `isNonPreferredCivsDisabled` | `isNonPreferredCivsDisabled()` |
| `isRumbleAvailable` | `isRumbleAvailable()` |
| `isSessionStartup` | `isSessionStartup()` |
| `isShowIntroSequences` | `isShowIntroSequences()` |
| `isShowODRDownloadPrompt` | `isShowODRDownloadPrompt()` |
| `isTouchEnabled` | `isTouchEnabled()` |
| `loadAsset` | `loadAsset(assetName)` |
| `lockCursor` | `lockCursor(arg0)` |
| `lookup` | `lookup(eventClass)` |
| `minimapToWorld` | `minimapToWorld({ x)` |
| `moveFixedMarkerImmediate` | `moveFixedMarkerImmediate(miniCursorMarker, { x, y, z)` |
| `notifyLoadingCurtainReady` | `notifyLoadingCurtainReady()` |
| `notifyUIReady` | `notifyUIReady()` |
| `notifyUIReadyForEvents` | `notifyUIReadyForEvents()` |
| `panelDefault` | `panelDefault()` |
| `panelEnd` | `panelEnd(targetClassName, panelContent, viewChangeMethod, arg3)` |
| `panelStart` | `panelStart(targetClassName, panelContent, viewChangeMethod, arg3)` |
| `playUnitSelectSound` | `playUnitSelectSound(unitType)` |
| `popFilter` | `popFilter()` |
| `pushGaussianBlurFilter` | `pushGaussianBlurFilter(arg0)` |
| `pushGlobalColorFilter` | `pushGlobalColorFilter({ saturation)` |
| `pushRegionColorFilter` | `pushRegionColorFilter(arg0, arg1, OUTER_REGION_OVERLAY_FILTER)` |
| `randomInt` | `randomInt(arg0, length - 1)` |
| `referenceCurrentEvent` | `referenceCurrentEvent()` |
| `refreshInput` | `refreshInput()` |
| `refreshPlayerColors` | `refreshPlayerColors()` |
| `registerCursor` | `registerCursor(NotAllowed, CANT_PLACE, arg2)` |
| `releaseEventID` | `releaseEventID(eventReference)` |
| `releaseMarker` | `releaseMarker(leader3DRevealFlagMarker)` |
| `reloadUI` | `reloadUI()` |
| `requestCinematic` | `requestCinematic(plot)` |
| `requestPortrait` | `requestPortrait(unitType, unitType, isUnique ? "UnitPortraitsBG_UNIQUE")` |
| `revertApplicationOptions` | `revertApplicationOptions()` |
| `revertNetworkOptions` | `revertNetworkOptions()` |
| `roundDirectionToHex` | `roundDirectionToHex(dx, dy)` |
| `screenTypeAction` | `screenTypeAction(CLOSE, SOCIAL)` |
| `sendAudioEvent` | `sendAudioEvent(improvementEvent)` |
| `sendAudioEventWithFinishedCallback` | `sendAudioEventWithFinishedCallback(voTag)` |
| `setApplicationOption` | `setApplicationOption(arg0, arg1, arg2)` |
| `setClipboardText` | `setClipboardText(arg0)` |
| `setCursorByType` | `setCursorByType(NotAllowed)` |
| `setCursorSize` | `setCursorSize({ i)` |
| `setDiploRibbonIndex` | `setDiploRibbonIndex(firstLeaderIndex)` |
| `setDisconnectionPopupWasShown` | `setDisconnectionPopupWasShown(arg0)` |
| `setGlobalScale` | `setGlobalScale(arg0)` |
| `setOOBEGraphicsRestart` | `setOOBEGraphicsRestart()` |
| `setOption` | `setOption(RIBBON_DISPLAY_OPTION_SET, RIBBON_DISPLAY_OPTION_TYPE, optionName, enable ? 1)` |
| `setPlotLocation` | `setPlotLocation(x, y, plotIndex)` |
| `setShowODRDownloadPrompt` | `setShowODRDownloadPrompt(arg0)` |
| `setTouchscreenTapDelay` | `setTouchscreenTapDelay(clickDuration)` |
| `setUnitVisibility` | `setUnitVisibility(arg0)` |
| `setViewExperience` | `setViewExperience(newExperience)` |
| `shouldDisableIntroAfterFirstPlay` | `shouldDisableIntroAfterFirstPlay()` |
| `shouldDisplayBenchmarkingTools` | `shouldDisplayBenchmarkingTools()` |
| `shouldDisplayOOBLegal` | `shouldDisplayOOBLegal()` |
| `shouldIncludeAppleCredit` | `shouldIncludeAppleCredit()` |
| `shouldShowAdditionalContent` | `shouldShowAdditionalContent()` |
| `shouldShowDisconnectionPopup` | `shouldShowDisconnectionPopup()` |
| `shouldShowHighEndAssetsDownloadOption` | `shouldShowHighEndAssetsDownloadOption()` |
| `showCursor` | `showCursor()` |
| `startHighEndAssetsDownload` | `startHighEndAssetsDownload()` |
| `supportsAutoMatching` | `supportsAutoMatching()` |
| `supportsDLC` | `supportsDLC()` |
| `supportsHIDPI` | `supportsHIDPI()` |
| `supportsMultiplayer` | `supportsMultiplayer()` |
| `supportsTextToSpeech` | `supportsTextToSpeech()` |
| `supportsTouchscreenTapDelay` | `supportsTouchscreenTapDelay()` |
| `toggleGameCenterAccessPoint` | `toggleGameCenterAccessPoint(arg0, BottomLeading)` |
| `triggerCinematic` | `triggerCinematic(location)` |
| `triggerVFXAtPlot` | `triggerVFXAtPlot(vfxName, location, { x, { angle)` |
| `triggerVFXAtPos` | `triggerVFXAtPos(arg0, { x, y, z)` |
| `useDefaultCustomReligionName` | `useDefaultCustomReligionName()` |
| `useReadOnlyInputMappingScreen` | `useReadOnlyInputMappingScreen()` |
| `viewChanged` | `viewChanged(viewID)` |
| `wrapWorldPosition` | `wrapWorldPosition(pos, { x)` |

#### Properties

| Property | Type |
|----------|------|
| `AssetID` | — |
| `BorderOverlay` | — |
| `BorderStyle` | — |
| `Cinematic` | — |
| `Color` | PlayerColor |
| `ColorFilter` | — |
| `Control` | — |
| `Debug` | — |
| `ForegroundCamera` | — |
| `HexGridOverlay` | — |
| `Marker` | — |
| `ModelGroup` | — |
| `ModelInstance` | — |
| `ModelParams` | — |
| `OverlayGroup` | — |
| `Player` | ComponentID |
| `Plot` | — |
| `PlotOverlay` | — |
| `PlotSet` | — |
| `SpriteGrid` | — |
| `SpriteParams` | — |
| `TextParams` | — |
| `VFXParams` | — |

### WorldBuilder

#### Properties

| Property | Type |
|----------|------|
| `MapPlots` | — |

### WorldUI

#### Methods

| Method | Signature |
|--------|-----------|
| `addBackgroundLayer` | `addBackgroundLayer(arg0, arg1)` |
| `addMaskedBackgroundLayer` | `addMaskedBackgroundLayer(backgroundName, arg1, {
					stretch)` |
| `clearBackground` | `clearBackground()` |
| `createFixedMarker` | `createFixedMarker({ x, y, z)` |
| `createModelGroup` | `createModelGroup(arg0)` |
| `createOverlayGroup` | `createOverlayGroup(arg0, UNIT_MOVEMENT_SKIRT, { x)` |
| `createSpriteGrid` | `createSpriteGrid(name + "_Background", FixedBillboard)` |
| `getDirection` | `getDirection(x, y)` |
| `getPlotAt` | `getPlotAt(controllerCursor, arg1)` |
| `getPlotLocation` | `getPlotLocation(desiredDestination, { x, TERRAIN) → float3` |
| `getScreenPlotPos` | `getScreenPlotPos(plotCursorCoords)` |
| `getScreenPos` | `getScreenPos(controllerCursor)` |
| `hash` | `hash(arg0)` |
| `isAssetLoaded` | `isAssetLoaded(currentPreloadingAsset)` |
| `loadAsset` | `loadAsset(assetName)` |
| `minimapToWorld` | `minimapToWorld({ x)` |
| `moveFixedMarkerImmediate` | `moveFixedMarkerImmediate(miniCursorMarker, { x, y, z)` |
| `popFilter` | `popFilter()` |
| `pushGaussianBlurFilter` | `pushGaussianBlurFilter(arg0)` |
| `pushGlobalColorFilter` | `pushGlobalColorFilter({ saturation)` |
| `pushRegionColorFilter` | `pushRegionColorFilter(arg0, arg1, OUTER_REGION_OVERLAY_FILTER)` |
| `releaseMarker` | `releaseMarker(leader3DRevealFlagMarker)` |
| `requestCinematic` | `requestCinematic(plot)` |
| `requestPortrait` | `requestPortrait(unitType, unitType, isUnique ? "UnitPortraitsBG_UNIQUE")` |
| `roundDirectionToHex` | `roundDirectionToHex(dx, dy)` |
| `setUnitVisibility` | `setUnitVisibility(arg0)` |
| `triggerCinematic` | `triggerCinematic(location)` |
| `triggerVFXAtPlot` | `triggerVFXAtPlot(vfxName, location, { x, { angle)` |
| `triggerVFXAtPos` | `triggerVFXAtPos(arg0, { x, y, z)` |
| `wrapWorldPosition` | `wrapWorldPosition(pos, { x)` |

#### Properties

| Property | Type |
|----------|------|
| `AssetID` | — |
| `BorderOverlay` | — |
| `BorderStyle` | — |
| `Cinematic` | — |
| `ColorFilter` | — |
| `ForegroundCamera` | — |
| `HexGridOverlay` | — |
| `Marker` | — |
| `ModelGroup` | — |
| `ModelInstance` | — |
| `ModelParams` | — |
| `OverlayGroup` | — |
| `Plot` | — |
| `PlotOverlay` | — |
| `PlotSet` | — |
| `SpriteGrid` | — |
| `SpriteParams` | — |
| `TextParams` | — |
| `VFXParams` | — |

### engine

#### Methods

| Method | Signature |
|--------|-----------|
| `AddOrRemoveOnHandler` | `AddOrRemoveOnHandler(name, callback, context \|\| engine)` |
| `BindingsReady` | `BindingsReady(arg0, arg1, arg2, arg3)` |
| `RemoveOnHandler` | `RemoveOnHandler(name, handler, context \|\| engine)` |
| `addDataBindEventListner` | `addDataBindEventListner(arg0, onUpdateWholeModel)` |
| `call` | `call(SPEAK, text, volume, speed, lang)` |
| `createJSModel` | `createJSModel(observableName, CityCaptureChooser)` |
| `off` | `off(OnChanged, onNetworkConnectionStatusChangedListener, arg2)` |
| `on` | `on(OnChanged, automationTestXRScreenshotAllSeuratsListener, context)` |
| `registerBindingAttribute` | `registerBindingAttribute(arg0, LocalizationDataBoundAttributeHandler)` |
| `reloadLocalization` | `reloadLocalization()` |
| `synchronizeModels` | `synchronizeModels()` |
| `trigger` | `trigger(arg0, actionName, status, x, y)` |
| `updateWholeModel` | `updateWholeModel(CityCaptureChooser)` |

#### Properties

| Property | Type |
|----------|------|
| `SendMessage` | — |
| `TriggerEvent` | — |
| `addSynchronizationDependency` | — |
| `createObservableModel` | — |
| `dependency` | — |
| `enableImmediateLayout` | — |
| `events` | — |
| `executeImmediateLayoutSync` | — |
| `hasAttachedUpdateListner` | — |
| `isAttached` | — |
| `isImmediateLayoutEnabled` | — |
| `mock` | — |
| `onUpdateWholeModel` | — |
| `removeSynchronizationDependency` | — |
| `whenReady` | — |

---

## Player Sub-Objects

These are accessed on player instances, e.g. `Players.get(0).Cities.getCityIds()`

### AdvancedStart

#### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(iPlayer)` |

### AgeProgressManager

#### Methods

| Method | Signature |
|--------|-----------|
| `canTransitionToNextAge` | `canTransitionToNextAge(localPlayerID)` |
| `getCurrentAgeProgressionPoints` | `getCurrentAgeProgressionPoints() → number` |
| `getMaxAgeProgressionPoints` | `getMaxAgeProgressionPoints() → number` |
| `getMilestoneProgressionPoints` | `getMilestoneProgressionPoints(AgeProgressionMilestoneType)` |
| `isMilestoneComplete` | `isMilestoneComplete(AgeProgressionMilestoneType) → boolean` |

#### Properties

| Property | Type |
|----------|------|
| `ageCountdownStarted` | boolean |
| `getAgeCountdownLength` | — |
| `isAgeOver` | — |
| `isExtendedGame` | — |
| `isFinalAge` | — |

### BuildQueue

#### Properties

| Property | Type |
|----------|------|
| `CurrentProductionTypeHash` | — |
| `isEmpty` | — |

### Cities

#### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(observer)` |
| `getCities` | `getCities()` |
| `getCityIds` | `getCityIds()` |

### CityCommands

#### Methods

| Method | Signature |
|--------|-----------|
| `canStart` | `canStart(_cityID, CHANGE_GROWTH_MODE, { ConstructibleType, arg3) → OperationResult` |
| `canStartQuery` | `canStartQuery(id, PURCHASE, Constructible)` |
| `sendRequest` | `sendRequest(_cityID, CHANGE_GROWTH_MODE, operationArgs)` |

### CityOperations

#### Methods

| Method | Signature |
|--------|-----------|
| `canStart` | `canStart(selectedCityID, BUILD, { ConstructibleType, arg3)` |
| `canStartQuery` | `canStartQuery(id, BUILD, Constructible)` |
| `sendRequest` | `sendRequest(CityID, CONSIDER_TOWN_PROJECT, operationArgs)` |

### CityStates

#### Methods

| Method | Signature |
|--------|-----------|
| `canHaveBonus` | `canHaveBonus(localPlayerID, cityState, CityStateBonusType)` |
| `getBonusType` | `getBonusType(playerID) → CityStateBonusType` |
| `getCityStateBonusToSelect` | `getCityStateBonusToSelect(localPlayerID) → PlayerId` |

### Combat

#### Methods

| Method | Signature |
|--------|-----------|
| `getBestDefender` | `getBestDefender(location, selectedUnitID) → ComponentID` |
| `getDefensibleDistrict` | `getDefensibleDistrict(location) → ComponentID` |
| `simulateAttackAsync` | `simulateAttackAsync(id, args)` |
| `testAttackInto` | `testAttackInto(selectedUnitID, parameters) → CombatTypes` |
| `toString` | `toString()` |

### Constructibles

#### Methods

| Method | Signature |
|--------|-----------|
| `find` | `find(arg0)` |
| `getBuildingYieldFromGreatWorks` | `getBuildingYieldFromGreatWorks(yieldType, constructibleID)` |
| `getGreatWorkBuildings` | `getGreatWorkBuildings() → GreatWorkBuilding[]` |
| `getIds` | `getIds() → ConstructibleID[]` |
| `getNumGreatWorkSlots` | `getNumGreatWorkSlots(constructibleID)` |
| `getNumWonders` | `getNumWonders()` |
| `getYieldFromGreatWork` | `getYieldFromGreatWork(yieldType, $index) → number` |
| `isAdjacencyUnlocked` | `isAdjacencyUnlocked(ID)` |
| `lookup` | `lookup(constructibleToBeBuiltOnExpand) → ConstructibleDefinition` |

#### Properties

| Property | Type |
|----------|------|
| `length` | — |

### CrisisManager

#### Methods

| Method | Signature |
|--------|-----------|
| `getCrisisStageTriggerPercent` | `getCrisisStageTriggerPercent(arg0, arg1)` |
| `getCurrentCrisisStage` | `getCurrentCrisisStage(arg0)` |
| `getMaximumTurnsRemainingInCurrentCrisis` | `getMaximumTurnsRemainingInCurrentCrisis(arg0, crisisStage)` |
| `getMinimumTurnsRemainingInCurrentCrisis` | `getMinimumTurnsRemainingInCurrentCrisis(arg0, crisisStage)` |
| `isCrisisEnabled` | `isCrisisEnabled(arg0)` |

### Culture

#### Methods

| Method | Signature |
|--------|-----------|
| `GetCelebrationTypesForGovernment` | `GetCelebrationTypesForGovernment(GovernmentType) → string[]` |
| `get` | `get(localPlayerID) → PlayerCulture` |
| `getChosenIdeology` | `getChosenIdeology()` |
| `getGovernmentType` | `getGovernmentType()` |
| `getGreatWorkType` | `getGreatWorkType(greatWorkIndex)` |
| `getTurnsForNode` | `getTurnsForNode(nodeType)` |
| `isNodeUnlocked` | `isNodeUnlocked(arg0)` |

### Diplomacy

#### Methods

| Method | Signature |
|--------|-----------|
| `canDeclareWarOn` | `canDeclareWarOn(arg0)` |
| `canMakePeaceWith` | `canMakePeaceWith(arg0, arg1) → DiplomacyQueryResult` |
| `get` | `get(playerA)` |
| `getActionRelationshipDelta` | `getActionRelationshipDelta(target, actionType) → number[]` |
| `getActiveStage` | `getActiveStage(uniqueID)` |
| `getAgendaDescriptions` | `getAgendaDescriptions(selectedPlayerID) → string[]` |
| `getAgendaNames` | `getAgendaNames(selectedPlayerID) → string[]` |
| `getBaseDiplomaticActionDuration` | `getBaseDiplomaticActionDuration(actionType)` |
| `getCompletionData` | `getCompletionData(selectedActionID) → DiplomacyEventCompletionData` |
| `getDiplomaticEventData` | `getDiplomaticEventData(selectedActionID) → DiplomaticEventHeader` |
| `getEspionagePenaltyForReveal` | `getEspionagePenaltyForReveal(actionType, localPlayerID)` |
| `getFM_RevealCapitalsString` | `getFM_RevealCapitalsString(localPlayerID, otherPlayer) → string` |
| `getFirstMeetResponseCostAndRelDelta` | `getFirstMeetResponseCostAndRelDelta(greetingType, localPlayerID) → number[]` |
| `getInfluenceForBaseAction` | `getInfluenceForBaseAction(DIPLOMACY_ACTION_DECLARE_FORMAL_WAR, localPlayerID, selectedPlayerID) → number` |
| `getInfluenceForNextSupport` | `getInfluenceForNextSupport(uniqueID, localPlayerID, localPlayerID)` |
| `getInfluenceIndependentData` | `getInfluenceIndependentData(uniqueID) → InfluenceIndependentData` |
| `getJointEvents` | `getJointEvents(localPlayerID, hoveredPlayerID, arg2) → DiplomaticEventHeader[]` |
| `getNextCallToArms` | `getNextCallToArms(localPlayerID) → DiplomacyActionEventId` |
| `getOpposingPlayers` | `getOpposingPlayers(uniqueID)` |
| `getOpposingPlayersWithBonusEnvoys` | `getOpposingPlayersWithBonusEnvoys(uniqueID)` |
| `getPlayerEvents` | `getPlayerEvents(targetIndependent) → DiplomaticEventHeader[]` |
| `getProjectDataForUI` | `getProjectDataForUI(initialPlayer, targetPlayer != null && targetPlayer != GameContext.localPlayerID ? targetPlayer, NO_DIPLOMACY_TARGET, NO_DIPLOMACY_ACTION_GROUP, arg4, NO_DIPLOMACY_TARGET) → DiplomaticProjectUIData[]` |
| `getRecentlyEndedDiplomaticEvents` | `getRecentlyEndedDiplomaticEvents(localPlayerID)` |
| `getResponseDataForUI` | `getResponseDataForUI(id)` |
| `getStages` | `getStages(uniqueID)` |
| `getSupportingPlayersWithBonusEnvoys` | `getSupportingPlayersWithBonusEnvoys(uniqueID)` |
| `getWarData` | `getWarData(uniqueID, localPlayerID) → WarData` |
| `hasAllied` | `hasAllied(initialPlayer)` |
| `hasMet` | `hasMet(localPlayerID, owner)` |
| `hasTeammate` | `hasTeammate(id)` |
| `isAtWarWith` | `isAtWarWith(playerId)` |
| `isProjectCanceled` | `isProjectCanceled(selectedActionID)` |
| `modifyByGameSpeed` | `modifyByGameSpeed(RandomInitialProgress) → number` |

### DiplomacyDeals

#### Methods

| Method | Signature |
|--------|-----------|
| `addItemToWorkingDeal` | `addItemToWorkingDeal(currentWorkingDealID!, initialPeaceDealItem)` |
| `clearWorkingDeal` | `clearWorkingDeal(currentWorkingDealID)` |
| `getDealIds` | `getDealIds(id)` |
| `getPossibleWorkingDealItems` | `getPossibleWorkingDealItems(workingDealId, localPlayerID, CITIES) → DiplomacyDealItem[]` |
| `getWorkingDeal` | `getWorkingDeal(currentWorkingDealID!) → DiplomacyDeal` |
| `getWorkingDealItem` | `getWorkingDealItem(currentWorkingDealID!, itemID) → DiplomacyDealItem` |
| `hasPendingDeal` | `hasPendingDeal(thisPlayerID, _selectedPlayerID)` |
| `removeItemFromWorkingDeal` | `removeItemFromWorkingDeal(currentWorkingDealID!, id)` |
| `sendWorkingDeal` | `sendWorkingDeal(currentWorkingDealID, PROPOSED)` |

### DiplomacySessions

#### Methods

| Method | Signature |
|--------|-----------|
| `closeSession` | `closeSession(ourDiplomacySession)` |
| `getKeyName` | `getKeyName(responseTypeHash)` |
| `getKeyNameOrNumber` | `getKeyNameOrNumber(StatementType) → string` |
| `sendResponse` | `sendResponse(sessionId, localPlayerID, Key)` |

### DiplomacyTreasury

#### Properties

| Property | Type |
|----------|------|
| `diplomacyBalance` | — |

### Districts

#### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(playerID) → PlayerDistricts` |
| `lookup` | `lookup(AdjacentDistrict) → DistrictDefinition` |

### EconomicRules

#### Methods

| Method | Signature |
|--------|-----------|
| `adjustForGameSpeed` | `adjustForGameSpeed(arg0)` |

### Experience

#### Properties

| Property | Type |
|----------|------|
| `experiencePoints` | — |
| `experienceToNextLevel` | — |
| `getLevel` | — |
| `getStoredCommendations` | — |
| `getStoredPromotionPoints` | — |
| `getTotalPromotionsEarned` | — |

### Health

#### Properties

| Property | Type |
|----------|------|
| `damage` | — |
| `maxDamage` | — |

### IndependentPowers

#### Methods

| Method | Signature |
|--------|-----------|
| `getDistanceToNearestIndependent` | `getDistanceToNearestIndependent(plotCoord) → number` |
| `getIndependentHostility` | `getIndependentHostility(independentID, localObserverID) → string` |
| `getIndependentPlayerIDAt` | `getIndependentPlayerIDAt(x, y) → PlayerId` |
| `getIndependentPlayerIDFromUnit` | `getIndependentPlayerIDFromUnit(viewingObjectID) → PlayerId` |
| `getIndependentPlayerIDWithUnitsAt` | `getIndependentPlayerIDWithUnitsAt(x, y)` |
| `getIndependentRelationship` | `getIndependentRelationship(independentID, localObserverID) → IndependentRelationship` |
| `independentName` | `independentName(selectedPlayerID) → string` |
| `independentVillageDiscoveredByPlayer` | `independentVillageDiscoveredByPlayer(independentID, localPlayerID)` |
| `isIndependentEncampment` | `isIndependentEncampment(independentID) → boolean` |

### Influence

#### Methods

| Method | Signature |
|--------|-----------|
| `getSuzerain` | `getSuzerain() → PlayerId` |

### LegacyPaths

#### Methods

| Method | Signature |
|--------|-----------|
| `getVictoryPointsFromPlayer` | `getVictoryPointsFromPlayer($hash, id)` |
| `lookup` | `lookup(LegacyPathType)` |

### Movement

#### Properties

| Property | Type |
|----------|------|
| `canMove` | — |
| `movementMovesRemaining` | — |

### Notifications

#### Methods

| Method | Signature |
|--------|-----------|
| `activate` | `activate(endTurnBlockingNotificationId)` |
| `canUserDismissNotification` | `canUserDismissNotification(notification)` |
| `clearNotifAudioTracking` | `clearNotifAudioTracking(notificationId)` |
| `dismiss` | `dismiss(_notificationId)` |
| `find` | `find(endTurnBlockingNotificationId) → Notification` |
| `findEndTurnBlocking` | `findEndTurnBlocking(localPlayerID, endTurnBlockingType) → ComponentID` |
| `getBlocksTurnAdvancement` | `getBlocksTurnAdvancement(entryTopId)` |
| `getEndTurnBlockingType` | `getEndTurnBlockingType(localPlayerID) → EndTurnBlockingType` |
| `getIdsForPlayer` | `getIdsForPlayer(localPlayer, DISMISSED) → ComponentID[]` |
| `getMessage` | `getMessage(endTurnBlockingNotificationId)` |
| `getPlayedAudioOnTurn` | `getPlayedAudioOnTurn(notificationID, turn)` |
| `getSeverity` | `getSeverity(notificationId)` |
| `getSummary` | `getSummary(notificationId)` |
| `getType` | `getType(notificationId) → number` |
| `getTypeName` | `getTypeName(notificationType) → string` |
| `lookup` | `lookup(Type)` |
| `setPlayedAudioOnTurn` | `setPlayedAudioOnTurn(notificationID, turn)` |

### PlacementRules

#### Methods

| Method | Signature |
|--------|-----------|
| `getValidOceanNavalLocation` | `getValidOceanNavalLocation(iPlayer)` |

### PlayerOperations

#### Methods

| Method | Signature |
|--------|-----------|
| `canStart` | `canStart(localPlayerID, CHOOSE_NARRATIVE_STORY_DIRECTION, actionOperationArguments, arg3) → OperationResult` |
| `sendRequest` | `sendRequest(localPlayerID, CHOOSE_NARRATIVE_STORY_DIRECTION, actionOperationArguments)` |

### ProgressionTrees

#### Methods

| Method | Signature |
|--------|-----------|
| `canEverUnlock` | `canEverUnlock(localPlayerID, nodeType)` |
| `find` | `find(arg0)` |
| `getLegendAttributeNodeLockedString` | `getLegendAttributeNodeLockedString(_player, nodeType)` |
| `getNode` | `getNode(localPlayerID, ProgressionTreeNodeType) → ProgressionTreeNode` |
| `getNodeState` | `getNodeState(playerId, nodeType) → ProgressionTreeNodeState` |
| `getTree` | `getTree(localPlayerID, _sourceProgressionTree) → ProgressionTree` |
| `getTreeStructure` | `getTreeStructure(_sourceProgressionTree) → ProgressionTreeStructureNode[]` |
| `hasLegendUnlocked` | `hasLegendUnlocked(_player, nodeType)` |
| `lookup` | `lookup(ProgressionTree) → ProgressionTreeDefinition` |

### RandomEvents

#### Methods

| Method | Signature |
|--------|-----------|
| `lookup` | `lookup(eventType) → RandomEventDefinition` |

### Religion

#### Methods

| Method | Signature |
|--------|-----------|
| `canCreateReligion` | `canCreateReligion()` |
| `canHaveBelief` | `canHaveBelief(localPlayerID, $index)` |
| `get` | `get()` |
| `getPantheons` | `getPantheons() → BeliefType[]` |
| `getPlayerFromReligion` | `getPlayerFromReligion(ReligionType)` |
| `getReligionType` | `getReligionType()` |
| `hasBeenFounded` | `hasBeenFounded(selectedReligionType) → boolean` |
| `hasCreatedReligion` | `hasCreatedReligion()` |
| `isBeliefClaimable` | `isBeliefClaimable(BeliefType)` |

### Resources

#### Methods

| Method | Signature |
|--------|-----------|
| `getLocalResources` | `getLocalResources()` |
| `getNumFactoryResources` | `getNumFactoryResources()` |
| `getNumTreasureFleetResources` | `getNumTreasureFleetResources(arg0)` |
| `getOriginCity` | `getOriginCity(resourceValue)` |
| `getUniqueResourceName` | `getUniqueResourceName(uniqueResource)` |
| `lookup` | `lookup(resourceChosenIndex) → ResourceDefinition` |

#### Properties

| Property | Type |
|----------|------|
| `length` | — |

### Stats

#### Methods

| Method | Signature |
|--------|-----------|
| `getNetYield` | `getNetYield(YIELD_HAPPINESS)` |

#### Properties

| Property | Type |
|----------|------|
| `numSettlements` | — |
| `settlementCap` | — |

### Techs

#### Methods

| Method | Signature |
|--------|-----------|
| `getTurnsForNode` | `getTurnsForNode(nodeType)` |

### Trade

#### Methods

| Method | Signature |
|--------|-----------|
| `countPlayerTradeRoutes` | `countPlayerTradeRoutes()` |
| `isConnectedToOwnersCapitalByLand` | `isConnectedToOwnersCapitalByLand()` |
| `isInRailNetwork` | `isInRailNetwork()` |
| `isInTradeNetwork` | `isInTradeNetwork()` |

### Treasury

#### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(localPlayerID)` |

#### Properties

| Property | Type |
|----------|------|
| `goldBalance` | — |

### UnitCommands

#### Methods

| Method | Signature |
|--------|-----------|
| `canStart` | `canStart(selectedUnitID, MAKE_TRADE_ROUTE, CommandArguments, arg3) → OperationResult` |
| `forEach` | `forEach(arg0)` |
| `lookup` | `lookup(arg0) → UnitCommandDefinition` |
| `sendRequest` | `sendRequest(selectedUnitID, MAKE_TRADE_ROUTE, actionParams)` |

### UnitOperations

#### Methods

| Method | Signature |
|--------|-----------|
| `canStart` | `canStart(unitID, operationName, parameters, arg3) → OperationResult` |
| `forEach` | `forEach(arg0)` |
| `lookup` | `lookup(arg0) → UnitOperationDefinition` |
| `sendRequest` | `sendRequest(unitID, operationName, args)` |

### Units

#### Methods

| Method | Signature |
|--------|-----------|
| `filter` | `filter(arg0)` |
| `find` | `find(arg0)` |
| `forEach` | `forEach(arg0)` |
| `getBuildUnit` | `getBuildUnit(arg0)` |
| `getNumUnitsOfType` | `getNumUnitsOfType(UnitType)` |
| `getUnitIds` | `getUnitIds() → ComponentID[]` |
| `getUnitTypesUnlockedWithTag` | `getUnitTypesUnlockedWithTag(tag, arg1) → UnitType[]` |
| `getUnitTypesWithTag` | `getUnitTypesWithTag(tag) → UnitType[]` |
| `getUnits` | `getUnits() → Unit[]` |
| `lookup` | `lookup(playerMerchantType) → UnitDefinition` |

#### Properties

| Property | Type |
|----------|------|
| `length` | — |

### Unlocks

#### Methods

| Method | Signature |
|--------|-----------|
| `getProgressForPlayer` | `getProgressForPlayer(UnlockType, localPlayerID)` |

### VictoryManager

#### Methods

| Method | Signature |
|--------|-----------|
| `getLatestPlayerDefeat` | `getLatestPlayerDefeat(localPlayerID) → DefeatType` |
| `getVictories` | `getVictories() → VictoryManagerLibrary_VictoryInfo[]` |

### Yields

#### Methods

| Method | Signature |
|--------|-----------|
| `extractYieldChangesData` | `extractYieldChangesData(yieldChanges, yieldType)` |
| `findIndex` | `findIndex(arg0)` |
| `forEach` | `forEach((yieldDef)` |
| `getResourceYields` | `getResourceYields()` |
| `getTradeYields` | `getTradeYields()` |
| `lookup` | `lookup(yieldType)` |

#### Properties

| Property | Type |
|----------|------|
| `length` | — |
