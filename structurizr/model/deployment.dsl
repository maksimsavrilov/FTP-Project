deploymentEnvironment "Production" {

    deploymentNode "Master Node" {
        masterInstance = containerInstance hosting.master
        databaseInstance = containerInstance hosting.database
    }

    deploymentNode "Authentication Node" {
       authServiceInstance = softwareSystemInstance authService
    }

    deploymentNode "Worker Node" {
        webAgentInstance = containerInstance hosting.webAgent
        dnsAgentInstance = containerInstance hosting.dnsAgent
        mailAgentInstance = containerInstance hosting.mailAgent

        nginxRuntime = infrastructureNode "Nginx Runtime" {
            description "Host-managed Nginx runtime outside the Web Agent container"
            technology "nginx"
            -> webAgentInstance "REST/HTTP: publish / validate / reload / status"
        }

        nginxLifecycleManager = infrastructureNode "Nginx Lifecycle Manager" {
            description "Host-side supervisor that owns generated config files, validation and service reload operations"
            technology "systemd / nginx"
            -> nginxRuntime "Owns config files and daemon lifecycle"
        }

        apacheRuntime = infrastructureNode "Apache Runtime" {
            description "Host-managed Apache runtime outside the Web Agent container"
            technology "Apache HTTP Server"
            -> webAgentInstance "REST/HTTP: publish / validate / reload / status"
        }
        
        apacheLifecycleManager = infrastructureNode "Apache Lifecycle Manager" {
            description "Host-side supervisor that owns generated config files, validation and service reload operations"
            technology "systemd / apache"
            -> apacheRuntime "Owns config files and daemon lifecycle"
        }

        infrastructureNode bindRuntime "BIND" {
            description "DNS server managed by DNS Agent"
            technology "Bind DNS Server"
            -> dnsAgentInstance "Managed by"
        }

        infrastructureNode postfixRuntime "Postfix" {
            description "SMTP server managed by Mail Agent"
            technology "Postfix SMTP Server"
            -> mailAgentInstance "Managed by"
        }

        infrastructureNode qmailRuntime "Qmail" {
            description "SMTP server managed by Mail Agent"
            technology "Qmail SMTP Server"
            -> mailAgentInstance "Managed by"
        }
        
        infrastructureNode CourierRuntime "Courier" {
            description "IMAP server managed by Mail Agent"
            technology "Courier IMAP Server"
            -> mailAgentInstance "Managed by"
        }
    }

    deploymentNode "Database Worker Node" {
        dbAgentInstance = containerInstance hosting.dbAgent

        infrastructureNode mysqlRuntime "MySQL" {
            description "MySQL server managed by DB agent"
            technology "mysql"
            -> dbAgentInstance "Managed by"
        }

        infrastructureNode postgresqlRuntime "PostgreSQL" {
            description "PostgreSQL server managed by DB agent"
            technology "postgresql"
            -> dbAgentInstance "Managed by"
        }  
    }
}
