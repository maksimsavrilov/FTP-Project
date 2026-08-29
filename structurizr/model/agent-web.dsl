webAgent = container "Web Agent" {
    description "Manages web hosting services"
    technology "Python"

    webApi = component "REST API" {
        description "REST endpoints exposed to Master"
        technology "FastAPI"
    }
    webAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }
    webDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired state from Master"
        technology "Python"
    }
    webReconciliation = component "Reconciliation Engine" {
        description "Compares desired and actual state and determines required changes"
        technology "Python"
    }
    webConfig = component "Web Configuration Manager" {
        description "Builds and manages web hosting configuration"
        technology "Python"
    }
    nginxManager = component "Nginx Manager" {
        description "Manages nginx configuration and lifecycle"
        technology "Python"
    }
    apacheManager = component "Apache Manager" {
        description "Manages Apache configuration and lifecycle"
        technology "Python"
    }
    webStateReporter = component "State & Health Reporter" {
        description "Reports actual state, health and heartbeat to Master"
        technology "Python"
    }

    # ====================================================
    # Внутренние связи компонентов Web Agent (перенесены сюда)
    # ====================================================
    webApi -> webAuth "Authenticates Master requests"
    webApi -> webDesiredState "Accepts desired state"
    webDesiredState -> webReconciliation "Triggers reconciliation"
    webReconciliation -> webConfig "Applies required configuration"
    webConfig -> nginxManager "Configures nginx"
    webConfig -> apacheManager "Configures Apache"
    webReconciliation -> webStateReporter "Reports reconciliation result"
    webStateReporter -> webApi "Exposes state and health information"
}
