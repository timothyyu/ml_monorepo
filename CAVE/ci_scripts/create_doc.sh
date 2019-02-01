#!/usr/bin/env sh

set -euo pipefail
echo "Starting Doc Push"

# Check if DOCPUSH is set
if ! [[ -z ${DOCPUSH+x} ]]; then
    
    if [[ "$DOCPUSH" == "true" ]]; then
        
        echo "DOCPUSH is TRUE"
        # install documentation building dependencies
        pip install --upgrade matplotlib pillow sphinx sphinx-gallery sphinx_bootstrap_theme

        # $1 is the branch name
        # $2 is the global variable where we set the script status
        
        if ! { [ $1 = "master" ] || [ $1 = "development" ]; }; then
            { echo "Not one of the allowed branches"; exit 0; }
        fi

        # delete any previous documentation folder
        if [ -d doc/$1 ]; then
            rm -rf doc/$1
        fi

        # create the documentation
        cd doc && make html 2>&1

        # create directory with branch name
        # the documentation for dev/stable from git will be stored here
        mkdir $1

        # get previous documentation from github
        git clone https://github.com/automl/CAVE.git --branch gh-pages --single-branch

        # copy previous documentation
        cp -r CAVE/. $1
        rm -rf CAVE

        if [ "$1" == "master" ]
        then
            output_folder="stable"
        else
            output_folder="dev"
        fi
        echo $output_folder

        # if the documentation for the branch exists, remove it
        if [ -d $1/$output_folder ]; then
            rm -rf $1/$output_folder
        fi

        # copy the updated documentation for this branch
        mkdir $1/$output_folder
        cp -r build/html/. $1/$output_folder


        # takes a variable name as an argument and assigns the script outcome to a
        # variable with the given name. If it got this far, the script was successful
        function set_return() {
            # $1 is the variable where we save the script outcome
            local __result=$1
            local  status='success'
            eval $__result="'$status'"
        }

        set_return "$2"
    fi
fi
# Workaround for travis failure
set +u
