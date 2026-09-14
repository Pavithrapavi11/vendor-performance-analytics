// Test IDs for the analytics dashboard.
export const ANALYTICS = {
    // Shell / header
    appHeader:            "app-header",
    datasetSelector:      "dataset-selector",
    datasetOption:        (id) => `dataset-option-${id}`,
    openUploadBtn:        "open-upload-btn",
    openSchemaBtn:        "open-schema-btn",
    deleteDatasetBtn:     "delete-dataset-btn",

    // Upload dialog
    uploadDialog:         "upload-dialog",
    uploadDialogClose:    "upload-dialog-close",
    uploadName:           "upload-name-input",
    uploadSubmit:         "upload-submit-btn",
    uploadError:          "upload-error",
    schemaDialog:         "schema-dialog",

    // Main body
    hero:                 "analytics-hero",
    loadingState:         "analytics-loading",
    errorState:           "analytics-error",

    // KPI cards
    kpiCardTotalPos:      "kpi-total-pos",
    kpiCardSpend:         "kpi-total-spend",
    kpiCardAvgOtd:        "kpi-avg-otd",
    kpiCardAvgDefect:     "kpi-avg-defect",
    kpiCardAvgScore:      "kpi-avg-score",
    kpiCardCoverage:      "kpi-coverage",

    // Recommendations
    pipSection:           "pip-section",
    rewardSection:        "reward-section",
    pipCard:              (vid) => `pip-card-${vid}`,
    rewardCard:           (vid) => `reward-card-${vid}`,

    // Charts
    chartMonthly:         "chart-monthly",
    chartBuckets:         "chart-buckets",
    chartCategory:        "chart-category",

    // Leaderboard
    leaderboardTable:     "leaderboard-table",
    leaderboardRow:       (vid) => `leaderboard-row-${vid}`,
    filterRegion:         "filter-region",
    filterCategory:       "filter-category",

    // Data health
    dataHealthPanel:      "data-health-panel",

    // Legacy — kept so /reports and /deck links still testid-addressable
    linkReport:           "link-report",
    linkDeck:             "link-deck",
    dashboardExecutive:   "dashboard-executive",
    dashboardDeepDive:    "dashboard-deep-dive",
};
