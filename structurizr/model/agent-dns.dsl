dnsAgent = container "DNS Agent" {
    description "Manages DNS services"
    technology "Python"

    dnsApi = component "REST API" {
        description "REST endpoints exposed to Master"
        technology "FastAPI"
    }
    dnsAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }
    dnsDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired DNS state from Master"
        technology "Python"
    }
    dnsReconciliation = component "Reconciliation Engine" {
        description "Compares desired DNS state with actual state"
        technology "Python"
    }
    dnsConfig = component "DNS Configuration Manager" {
        description "Manages DNS Agent configuration"
        technology "Python"
    }
    zoneManager = component "Zone Manager" {
        description "Creates, updates and removes DNS zones and records"
        technology "Python"
    }
    bindManager = component "BIND Manager" {
        description "Manages BIND configuration, validation and lifecycle"
        technology "Python"
    }
    dnsStateReporter = component "State & Health Reporter" {
        description "Reports actual DNS state, health and heartbeat to Master"
        technology "Python"
    }

    # Relationships
    dnsApi -> dnsAuth "Authenticates Master requests"
    dnsApi -> dnsDesiredState "Accepts desired DNS state"
    dnsDesiredState -> dnsReconciliation "Triggers reconciliation"
    dnsReconciliation -> dnsConfig "Applies required DNS configuration"
    dnsConfig -> zoneManager "Manages zones and records"
    zoneManager -> bindManager "Applies BIND configuration"
    dnsReconciliation -> dnsStateReporter "Reports reconciliation result"
    dnsStateReporter -> dnsApi "Exposes state and health information"
}
