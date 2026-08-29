mailAgent = container "Mail Agent" {
    description "Manages mail services"
    technology "Python"

    mailApi = component "REST API" {
       description "REST endpoints exposed to Master"
       technology "FastAPI"
    }
    mailAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }
    mailDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired mail state from Master"
        technology "Python"
    }
    mailReconciliation = component "Reconciliation Engine" {
        description "Compares desired mail state with actual state"
        technology "Python"
    }
    mailConfig = component "Mail Configuration Manager" {
        description "Manages mail service configuration"
        technology "Python"
    }
    mailManager = component "Mail Manager" {
        description "Manages the configured mail stack"
        technology "Python"
    }
    mailStateReporter = component "State & Health Reporter" {
        description "Reports actual mail state, health and heartbeat to Master"
        technology "Python"
    }

    # Relationships
    mailApi -> mailAuth "Authenticates Master requests"
    mailApi -> mailDesiredState "Accepts desired mail state"
    mailDesiredState -> mailReconciliation "Triggers reconciliation"
    mailReconciliation -> mailConfig "Applies required mail configuration"
    mailConfig -> mailManager "Manages mail stack"
    mailReconciliation -> mailStateReporter "Reports reconciliation result"
    mailStateReporter -> mailApi "Exposes state and health information"
}
