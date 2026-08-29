workspace "Hosting Control System" "Distributed hosting management system" {

    model {

        // ============================================================
        // People
        // ============================================================

        admin = person "Admin" {
            description "Manages the whole hosting infrastructure"
        }

        reseller = person "Reseller" {
            description "Manages users and subscriptions within assigned limits"
        }

        siteUser = person "Site User" {
            description "Manages own hosting services"
        }


        // ============================================================
        // Hosting Control System
        // ============================================================

        hosting = softwareSystem "Hosting Control System" {

            // ========================================================
            // CLI
            // ========================================================

            cli = container "CLI" {
                description "Unix-style command line interface"
                technology "Python"
            }


            // ========================================================
            // Master Application
            // ========================================================

            master = container "Master Application" {
                description "Control plane, REST API, business logic, scheduling and reconciliation"
                technology "Python / FastAPI"

                // ----------------------------------------------------
                // API
                // ----------------------------------------------------

                api = component "REST API" {
                    description "HTTP API endpoints exposed to CLI and other clients"
                    technology "FastAPI"
                }

                auth = component "Authentication & Authorization" {
                    description "Authenticates users and authorizes operations"
                    technology "Python"
                }


                // ----------------------------------------------------
                // Domain
                // ----------------------------------------------------

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


                // ----------------------------------------------------
                // Control Plane
                // ----------------------------------------------------

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


                // ----------------------------------------------------
                // Persistence
                // ----------------------------------------------------

                repositories = component "Repositories" {
                    description "Persistence layer for system state"
                    technology "Python / SQLAlchemy"
                }


                // ====================================================
                // Component relationships
                // ====================================================

                api -> auth "Authenticates and authorizes requests"

                api -> users "Manages users"
                api -> resellers "Manages resellers"
                api -> plans "Manages service plans"
                api -> subscriptions "Manages subscriptions"
                api -> services "Manages services"
                api -> resources "Manages resources"
                api -> nodes "Manages Worker Nodes"


                // ----------------------------------------------------
                // Domain relationships
                // ----------------------------------------------------

                resellers -> users "Manages users belonging to reseller"

                plans -> subscriptions "Defines subscription limits"

                subscriptions -> services "Owns services"
                
                // subscriptions -> domains "Owns domains"
                
                // domains -> websites "Contains websites"
                
                // websites -> services "Uses web service"

                plans -> resources "Defines resource limits"

                subscriptions -> resources "Consumes resources"


                // ----------------------------------------------------
                // Scheduling
                // ----------------------------------------------------

                services -> scheduler "Requests service placement"

                nodes -> scheduler "Provides node capabilities and availability"

                resources -> scheduler "Provides resource availability"

                scheduler -> reconciliation "Creates or updates service assignment and desired state"


                // ----------------------------------------------------
                // Reconciliation
                // ----------------------------------------------------

                reconciliation -> agentClient "Sends desired state and commands"

                agentClient -> reconciliation "Returns actual state and operation results"


                // ----------------------------------------------------
                // Persistence
                // ----------------------------------------------------

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


            // ========================================================
            // State Database
            // ========================================================

            database = container "State Database" {
                description "Stores users, subscriptions, service plans, resources, nodes, services and desired state"
                technology "PostgreSQL"
            }


            // ========================================================
            // Worker Agents
            // ========================================================

            webAgent = container "Web Agent" {
                description "Manages web hosting services"
                technology "Python"

                // ========================================================
                // Web Agent Components
                // ========================================================

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
            }

            dnsAgent = container "DNS Agent" {
                description "Manages DNS services"
                technology "Python"
                // ====================================================
                // DNS Agent Components
                // ====================================================

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


                // ====================================================
                // Component relationships
                // ====================================================

                dnsApi -> dnsAuth "Authenticates Master requests"

                dnsApi -> dnsDesiredState "Accepts desired DNS state"

                dnsDesiredState -> dnsReconciliation "Triggers reconciliation"

                dnsReconciliation -> dnsConfig "Applies required DNS configuration"

                dnsConfig -> zoneManager "Manages zones and records"

                zoneManager -> bindManager "Applies BIND configuration"

                dnsReconciliation -> dnsStateReporter "Reports reconciliation result"

                dnsStateReporter -> dnsApi "Exposes state and health information"
            }

            mailAgent = container "Mail Agent" {
                description "Manages mail services"
                technology "Python"
                // ====================================================
                // Mail Agent Components
                // ====================================================

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
 
 
                // ====================================================
                // Component relationships
                // ====================================================
 
                mailApi -> mailAuth "Authenticates Master requests"
                mailApi -> mailDesiredState "Accepts desired mail state"
                mailDesiredState -> mailReconciliation "Triggers reconciliation"
                mailReconciliation -> mailConfig "Applies required mail configuration"
                mailConfig -> mailManager "Manages mail stack"
                mailReconciliation -> mailStateReporter "Reports reconciliation result"
                mailStateReporter -> mailApi "Exposes state and health information"
            }

            dbAgent = container "DB Agent" {
                description "Manages database services"
                technology "Python"
            }



            // ========================================================
            // Container relationships
            // ========================================================

            cli -> master "Executes commands via REST/HTTP"

            master -> database "Reads and writes state"

            master -> webAgent "Controls and sends desired state via REST/HTTP"

            webAgent -> master "Reports actual state and heartbeat via REST/HTTP"

            master -> dnsAgent "Controls and sends desired state via REST/HTTP"

            dnsAgent -> master "Reports actual state and heartbeat via REST/HTTP"

            master -> mailAgent "Controls and sends desired state via REST/HTTP"

            mailAgent -> master "Reports actual state and heartbeat via REST/HTTP"

            master -> dbAgent "Controls and sends desired state via REST/HTTP"

            dbAgent -> master "Reports actual state and heartbeat via REST/HTTP"


            // ========================================================
            // Web Agent component relationships
            // ========================================================

            webApi -> webAuth "Authenticates Master requests"

            webApi -> webDesiredState "Accepts desired state"

            webDesiredState -> webReconciliation "Triggers reconciliation"

            webReconciliation -> webConfig "Applies required configuration"

            webConfig -> nginxManager  "Configures nginx"

            webConfig -> apacheManager  "Configures Apache"

            webReconciliation -> webStateReporter  "Reports reconciliation result"

            webStateReporter -> webApi  "Exposes state and health information"
        }


        // ============================================================
        // People relationships
        // ============================================================

        admin -> cli "Uses"

        reseller -> cli "Uses"

        siteUser -> cli "Uses"


        // ============================================================
        // Deployment model
        // ============================================================

        deploymentEnvironment "Production" {

            deploymentNode "Master Node" {

                masterInstance = containerInstance master
                databaseInstance = containerInstance database
            }


            deploymentNode "Worker Node" {

                webAgentInstance = containerInstance webAgent

                infrastructureNode nginxRuntime "nginx" {
                    description "Web server managed by Web Agent"
                    technology "nginx"

                    -> webAgentInstance "Managed by"
                }

                infrastructureNode apacheRuntime "Apache" {
                    description "Web server managed by Web Agent"
                    technology "Apache HTTP Server"

                    -> webAgentInstance "Managed by"
                }

                deploymentNode "DNS Agent" {
                    containerInstance dnsAgent
                }

                deploymentNode "Mail Agent" {
                    containerInstance mailAgent
                }
            }

            deploymentNode "Database Worker Node" {

                dbAgentInstance = containerInstance dbAgent
            }
        }
    }


    // ================================================================
    // Views
    // ================================================================

    views {

        // ------------------------------------------------------------
        // Level 1 — System Context
        // ------------------------------------------------------------

        systemContext hosting "SystemContext" {
            include admin
            include reseller
            include siteUser
            include hosting
            autolayout lr
        }


        // ------------------------------------------------------------
        // Level 2 — Containers
        // ------------------------------------------------------------

        container hosting "Containers" {
            include *
            autolayout lr
        }


        // ------------------------------------------------------------
        // Level 3 —  Components
        // ------------------------------------------------------------

        component master "MasterComponents" {
            include *
            autolayout lr
        }


        component webAgent "WebAgentComponents" {
           include *
           autolayout lr
        }

        component dnsAgent "DnsAgentComponents" {
           include *
           autolayout lr
        }
        
        component mailAgent "MailAgentComponents" {
           include *
           autolayout lr
        }


        // ------------------------------------------------------------
        // Deployment
        // ------------------------------------------------------------

        deployment hosting "Production" {
            include *
            autolayout lr
        }


        // ============================================================
        // Styles
        // ============================================================

        styles {

            element "Person" {
                shape person
                background "#08427b"
                color "#ffffff"
            }

            element "Software System" {
                background "#1168bd"
                color "#ffffff"
            }

            element "Container" {
                background "#438dd5"
                color "#ffffff"
            }

            element "Component" {
                background "#85bbf0"
                color "#000000"
            }

            element "Deployment Node" {
                background "#999999"
                color "#ffffff"
            }
        }
    }
}