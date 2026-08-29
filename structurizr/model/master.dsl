master = container "Master Application" {
    description "Control plane, REST API, business logic, scheduling and reconciliation"
    technology "Python / FastAPI"

    # API Components
    api = component "REST API" {
        description "HTTP API endpoints exposed to CLI and other clients"
        technology "FastAPI"
    }
    auth = component "Authentication & Authorization" {
        description "Authenticates users and authorizes operations"
        technology "Python"
    }

    # Domain Components
    users = component "User Management" {
        description "Manages Site Users and their lifecycle"
        technology "Python"
    }
    resellers = component "Reseller Management" {
        description "Manages Resellers and their users"
        technology "Python"
    }
    plans = component "Service Plan Management" {
        description "Manages service plans and resource limits hierarchy"
        technology "Python"
    }
    subscriptions = component "Subscription Management" {
        description "Manages user subscriptions, domains and their lifecycle"
        technology "Python"
    }
    services = component "Service Management" {
        description "Manages Web, DNS, Mail and DB services and their configuration"
        technology "Python"
    }
    resources = component "Resource Management" {
        description "Tracks resource allocation and limits"
        technology "Python"
    }
    nodes = component "Node Management" {
        description "Manages Worker Nodes, capabilities and health state"
        technology "Python"
    }

    # Control Plane Components
    scheduler = component "Scheduler" {
        description "Selects suitable Worker Nodes for services"
        technology "Python"
    }
    reconciliation = component "Reconciliation Manager" {
        description "Maintains desired state and reconciles it with Worker Agent actual state"
        technology "Python"
    }
    agentClient = component "Agent Client" {
        description "REST client used to communicate with Worker Agents"
        technology "Python / HTTP"
    }

    # Persistence Components
    repositories = component "Repositories" {
        description "Persistence layer for system state"
        technology "Python / SQLAlchemy"
    }

    # Relationships
    api -> auth "Authenticates and authorizes requests"
    api -> users "Manages users"
    api -> resellers "Manages resellers"
    api -> plans "Manages service plans"
    api -> subscriptions "Manages subscriptions"
    api -> services "Manages services"
    api -> resources "Manages resources"
    api -> nodes "Manages Worker Nodes"

    resellers -> users "Manages users belonging to reseller"
    plans -> subscriptions "Defines subscription limits"
    subscriptions -> services "Owns services"
    plans -> resources "Defines resource limits"
    subscriptions -> resources "Consumes resources"

    services -> scheduler "Requests service placement"
    nodes -> scheduler "Provides node capabilities and availability"
    resources -> scheduler "Provides resource availability"
    scheduler -> reconciliation "Creates or updates service assignment and desired state"

    reconciliation -> agentClient "Sends desired state and commands"
    agentClient -> reconciliation "Returns actual state and operation results"

    users -> repositories "Persists user state"
    resellers -> repositories "Persists reseller state"
    plans -> repositories "Persists service plans"
    subscriptions -> repositories "Persists subscriptions"
    services -> repositories "Persists services and desired state"
    resources -> repositories "Persists resource allocation"
    nodes -> repositories "Persists node state"
    scheduler -> repositories "Reads assignments and resource state"
    reconciliation -> repositories "Reads and updates desired state"
}
