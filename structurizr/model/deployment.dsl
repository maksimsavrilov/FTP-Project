deploymentEnvironment "Production" {

    deploymentNode "Master Node" {
        masterInstance = containerInstance hosting.master
        databaseInstance = containerInstance hosting.database
    }

    deploymentNode "Worker Node" {
        webAgentInstance = containerInstance hosting.webAgent
        dnsAgentInstance = containerInstance hosting.dnsAgent
        mailAgentInstance = containerInstance hosting.mailAgent

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
    }

    deploymentNode "Database Worker Node" {
        dbAgentInstance = containerInstance hosting.dbAgent

        infrastructureNode mysqlRuntime "MySQL" {
            description "MySQL server managed by DB agent"
            technology "mysql"
            -> dbAgentInstance "Managed by"
        }

        infrastructureNode postgresqlRuntime "PostgreSQL" {
            description "MySQL server managed by DB agent"
            technology "postgresql"
            -> dbAgentInstance "Managed by"
        }  
    }
}
