dbAgent = container "DB Agent" {
    description "Manages database services"
    technology "Python / FastAPI"

    dbApi = component "REST API" {
        description "REST endpoints exposed to Master"
        technology "FastAPI"
    }

    dbAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }

    dbDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired database state from Master"
        technology "Python"
    }

    dbReconciliation = component "Reconciliation Engine" {
        description "Compares desired database state with actual state"
        technology "Python"
    }

    dbConfig = component "Database Configuration Manager" {
        description "Manages database service configuration"
        technology "Python"
    }

    dbManager = component "Database Manager" {
        description "Manages the configured database engine"
        technology "Python"
    }

    dbStateReporter = component "State & Health Reporter" {
        description "Reports actual database state, health and heartbeat to Master"
        technology "Python"
    }

    dbApi -> dbAuth "Authenticates Master requests" "Python"
    dbApi -> dbDesiredState "Accepts and validates desired database state" "Python"

    dbDesiredState -> dbReconciliation "Triggers reconciliation" "Python"

    dbReconciliation -> dbConfig "Applies required database configuration" "Python"

    dbConfig -> dbManager "Manages database engine" "Python"

    dbReconciliation -> dbStateReporter "Reports reconciliation result" "Python"

    dbStateReporter -> dbApi "Exposes state and health information" "Python"
}