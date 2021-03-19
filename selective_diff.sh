#!/bin/bash

# Author: Lionel GUEZ

# Selective analysis of differences between directories based on file
# type and amount of difference. This script first compares briefly
# two directories. The two directories should be given as arguments of
# the script. If the directories contains text or DBF files with the
# same name and modestly different content then the script prints the
# detailed difference between them. If the directories contain NetCDF
# files with the same name and different content then the script
# compares further the header and data parts. The script prints the
# detailed differences between the header part, and between the dumps
# of the data parts if the number of different lines is small
# enough. The script optionally:

# - creates a NetCDF file with the NCO operator "ncbo" containing the
# difference and the relative difference between the original NetCDF
# files;

# - computes statistics of the differences.

# The user of this script needs to have the permission to write in the
# current directory.

# Non-standard utilities invoked in this script: ncdump, NCO,
# nccmp.py, max_diff_nc.sh, dbfdump, ndiff by Nelson Beebe,
# numdiff. ndiff and numdiff are not completely redundant.

# An exit status of 0 means no differences were found, 1 means some
# differences were found, and 2 means trouble.

##set -x

function cat_not_too_many
{
    # Argument: file name. Global variable used: size_lim.
    
    if (($(wc -l $1 |cut -f 1 -d " ") < size_lim))
    then
	cat $1
	echo
    else
	echo "Too many lines in diff output"
    fi
}

function nc_over_diff
{

    # This function compares two NetCDF files. The files have the same
    # name given by global variable "name". They are in two
    # directories that should be given as function arguments. The
    # function also uses the global variable "name0".

    declare -i filesize1 filesize2

    echo 

    # Headers:
    ncdump -h $1/$name > ${name0}_1.cdl
    ncdump -h $2/$name > ${name0}_2.cdl
    diff ${name0}_[12].cdl >diff_out

    if (($? == 0))
    then
	echo "Headers are identical."
    else
	echo "Headers are different."
	cat_not_too_many diff_out
    fi

    rm ${name0}_[12].cdl diff_out
    echo

    nccmp.py --data $1/$name $2/$name
    return_code=$?

    if (($return_code == 1))
    then
	echo "Data parts are different."
	filesize1=$(du $1/$name | cut -f 1)
	filesize2=$(du $2/$name | cut -f 1)
	if ((filesize1 <= 1024 && filesize2 <= 1024))
	then
	    ncdump $1/$name | csplit --silent - %^data:$%
	    mv xx00 ${name0}_1.cdl
	    ncdump $2/$name | csplit --silent - %^data:$%
	    mv xx00 ${name0}_2.cdl

	    diff --text ${name0}_[12].cdl >diff_out
            # (--text because undefined values may produce non-ascii
            # characters)

	    rm ${name0}_[12].cdl
	    echo "-- Differences between dumps of data parts of \"$name\""
	    cat_not_too_many diff_out
	    rm diff_out
	else
	    echo
	    echo "Files are too large (> 1 MiB) to dump"
	fi
	if [[ $subtract = y ]]
	then
            # Compute difference and relative difference between NetCDF files:
	    ncbo --op_typ=subtract --overwrite $2/$name $1/$name \
		 ${name0}_var.nc
	    if (($? == 0))
	    then
		echo "Created file \"${name0}_var.nc\"."
		ncbo --op_typ=divide --overwrite ${name0}_var.nc $1/$name \
		     ${name0}_rel_var.nc
		echo "Created file \"${name0}_rel_var.nc\"."
	    fi
	fi
	if [[ $statistics = y ]]
	then
            # Compute statistics of the difference between NetCDF files:
	    echo
	    echo "Statistics with \"max_diff_nc\" for \"$name\""
	    max_diff_nc.sh $1/$name $2/$name
	fi
    elif (($return_code >= 2))
    then
	exit $return_code
    fi
}

USAGE="Usage:
`basename $0` [-d] [-l limit] [-s] [-b] [-r] [-x PAT] directory directory

   -d      : create a NetCDF file containing differences for NetCDF files 
             with different data parts (default: do not create)
   -l limit: maximum number of lines for printing detailed differences
             (default 50)
   -s      : compute statistics for NetCDF files with different data parts
             (default: do not compute)
   -b      : only compare directories briefly (default: analyse each file
             after brief comparison of directories)
   -r      : report indentical directories
   -x PAT  : exclude files that match shell pattern PAT"

while getopts :dl:sbrx: argument
do
    case $argument in
	d) subtract=y;;
	l) size_lim=$OPTARG;;
	s) statistics=y;;
	b) brief=y;;
	r) report_identical=y;;
	x) PAT+=($OPTARG);;
	:) echo "Missing argument for switch $OPTARG"
	   exit 2;;
	\?) echo "$OPTARG: invalid switch"
	    echo "$USAGE"
	    exit 2;;
    esac
done

subtract=${subtract:-n}
size_lim=${size_lim:-50}
statistics=${statistics:-n}
brief=${brief:-n}
report_identical=${report_identical:-n}

shift $((OPTIND - 1))

if (($# != 2))
then
    echo "$USAGE" >&2
    exit 2
fi

if [[ ! -w $PWD ]]
then
    echo "You need to have write permission (for temporary files)"
    echo "in the current directory."
    exit 2
fi

type nccmp.py >/dev/null
if (($? != 0))
then
    echo "Please install nccmp.py."
    exit 2
fi

type ncdump >/dev/null
if (($? != 0))
then
    exit 2
fi

if [[ ! -d $1 || ! -d $2 ]]
then
    echo
    echo "Directories: $*"
    echo "Bad directories"
    exit 2
fi

# Compare directories briefly:

for p in ${PAT[@]}
do
    exclude_options="$exclude_options -x $p"
done

diff --recursive --brief $exclude_options $1 $2 2>&1 | grep "^Only in " \
							    >grep_out

declare -i n_diff=0
# (number of differing files)

declare -i n_id=0
# (number of identical files)

cd $1
unset exclude_options

for p in ${PAT[@]}
do
    exclude_options="$exclude_options ! -name $p"
done

find -type f $exclude_options >/tmp/file_list
cd - >/dev/null

while read filename
do
    if [[ -f $2/$filename ]]
    then
	# We have a file with the same name in the two directories

	suffix=${filename##*.}
	cmp --silent $1/$filename $2/$filename
	return_code=$?
	
	if (($return_code != 0)) && [[ $brief == n ]]
	then
	    # Sometimes the files have the same content but are not
	    # identical, so double-check:
	    if [[ $suffix == nc ]]
	    then
		nccmp.py --silent $1/$filename $2/$filename
		return_code=$?
	    elif [[ $suffix == dbf ]]
	    then
		name0=$(basename $filename .dbf)
		dbfdump $1/$filename >${name0}_1_dbfdump.txt
		dbfdump $2/$filename >${name0}_2_dbfdump.txt
		cmp --silent ${name0}_[12]_dbfdump.txt
		return_code=$?
		rm ${name0}_[12]_dbfdump.txt
	    fi
	fi
	    
	if (($return_code != 0))
	then
            # Different content
	    ((n_diff = n_diff + 1))
	    diff_file[n_diff]=$filename
	else
	    # Same content
	    ((n_id = n_id + 1))
	    id_file[n_id]=$filename
	fi
    fi
done </tmp/file_list

rm /tmp/file_list

if [[ $report_identical == y || -s grep_out ]] || ((n_diff != 0))
then
    echo
    echo "Directories: $*"
    cat grep_out
    echo
    IFS="
"
    echo "Differing files:"
    echo
    echo "${diff_file[*]}"
    echo
    echo "Number of files found:"
    echo $n_diff
    echo
    echo "Identical files:"
    echo
    echo "${id_file[*]}"
    echo
    echo "Number of files found:"
    echo $n_id
    echo

    if [[ $brief == n ]]
    then
	# Analyse each file
	for name in "${diff_file[@]}"
	do
	    if [[ ! -f "$1/$name" ]]
	    then
		echo "Broken link: $1/$name"
	    elif [[ ! -f "$2/$name" ]]
	    then
		echo "Broken link: $2/$name"
	    else
		suffix=${name##*.}

		if [[ $suffix == txt || $suffix == json \
			  || ($suffix != nc && $suffix != csv \
				  && $(file "$1/$name") == *text*) ]]
		then
		    text_file=true
		else
		    text_file=false
		fi

		if [[ $text_file == true || $suffix == @(nc|dbf|csv) ]]
		then
		    # We have a text, NetCDF, DBF or CSV file
		    name0=$(basename $name .$suffix)
		    echo
		    echo '*******************************************'
		    echo
		    echo $name
		    if [[ $text_file == true ]]
		    then
			diff --ignore-all-space $1/$name $2/$name >diff_out
			
			if [[ -s diff_out ]]
			then
			    cat_not_too_many diff_out
			else
			    echo "Only white space difference"
			fi
			
			echo
			rm diff_out
		    elif [[ $suffix == dbf ]]
		    then
			dbfdump $1/$name >${name0}_1_dbfdump.txt
			dbfdump $2/$name >${name0}_2_dbfdump.txt

			echo "dbfdumps of \"$name\" compared with ndiff, "\
			     "tolerance 1e-7:"
			ndiff -relerr 1e-7 ${name0}_[12]_dbfdump.txt >ndiff_out
			cat_not_too_many ndiff_out

			echo "dbfdumps of \"$name\" compared with numdiff, "\
			     "tolerance 1e-7:"
			numdiff -r 1e-7 ${name0}_[12]_dbfdump.txt >ndiff_out
			cat_not_too_many ndiff_out
			
			rm ${name0}_[12]_dbfdump.txt ndiff_out
		    elif [[ $suffix == csv ]]
		    then
			echo "Comparison with ndiff, tolerance 1e-7::"
			ndiff -relerr 1e-7 $1/$name $2/$name >ndiff_out
			cat_not_too_many ndiff_out
			
			echo "Comparison with numdiff, tolerance 1e-7:"
			numdiff -r 1e-7 $1/$name $2/$name >ndiff_out
			cat_not_too_many ndiff_out
			
			rm ndiff_out
			echo
		    else
			nc_over_diff $*
		    fi
		fi
	    fi
	done
    fi
fi

if ((n_diff == 0)) && [[ ! -s grep_out ]]
then
    rm grep_out
    exit 0
else
    rm grep_out
    exit 1
fi
