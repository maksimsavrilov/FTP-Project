dynamic hosting "UserCreation" {

    admin -> hosting.cli "Starts user creation command"

    hosting.cli -> hosting.master "Requests user creation via REST"

    hosting.master -> hosting.database "Creates User record"

    hosting.master -> hosting.cli "Returns User ID"

    hosting.cli -> admin "Shows created user"

    autoLayout lr
}
