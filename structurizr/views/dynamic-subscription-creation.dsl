dynamic hosting "SubscriptionCreation" {

    admin -> hosting.cli "Starts subscription creation command"

    hosting.cli -> hosting.master "Requests Subscription creation for a User based on a Hosting Plan via REST"

    hosting.master -> hosting.database "Reads User account"

    hosting.master -> hosting.database "Reads Hosting Plan limits and permissions"

    hosting.master -> hosting.database "Validates and reserves subscription resource limits and object limits from the Hosting Plan to the User"

    hosting.master -> hosting.database "Creates Subscription record bound to User and Hosting Plan"

    hosting.master -> hosting.cli "Returns Subscription ID"

    hosting.cli -> admin "Shows created subscription"

    autoLayout lr
}
